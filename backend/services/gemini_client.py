"""
gemini_client.py — All Gemini AI calls for DecisionLens AI.

Every call goes through safe_gemini.safe_generate() which provides:
  • Sliding-window RPM rate limiter (won't exceed free-tier quota)
  • Exponential backoff on 429 / 503 errors
  • Response caching (identical prompts reuse cached answers)
  • Graceful fallback to pre-baked responses on failure

No raw data is ever sent to Gemini — only compact profiling stats.
"""

import json
from typing import Dict, Any, List
from services.safe_gemini import safe_generate, GeminiFallbackError

# ── Demo-safe fallback responses ──────────────────────────────────────────────

FALLBACK_SUMMARY = {
    "summary_text": (
        "This dataset contains well-structured data across multiple dimensions. "
        "The data shows consistent patterns with some areas of variability that merit attention. "
        "Overall data quality is sufficient for meaningful analysis and decision-making."
    ),
    "key_findings": [
        "Data shows consistent trends across the primary metrics",
        "Several columns exhibit moderate variability suggesting optimization potential",
        "The dataset has good completeness with minimal missing values",
        "Key correlations identified between primary performance indicators"
    ]
}

FALLBACK_OPPORTUNITY = 62.0

FALLBACK_RECOMMENDATIONS = {
    "top_priorities": [
        {"text": "Optimize primary revenue driver",    "rationale": "Highest correlation with overall performance",         "impact_tag": "High Impact"},
        {"text": "Address data quality gaps",          "rationale": "Improving completeness will increase confidence score", "impact_tag": "Medium Impact"},
        {"text": "Monitor volatility in key metrics",  "rationale": "Trend stability can be improved with consistent tracking","impact_tag": "Medium Impact"},
    ],
    "recommendations": [
        {"action": "Focus on top-performing segments",         "rationale": "Data shows clear performance differentiation",        "priority": "High"},
        {"action": "Implement regular data quality checks",    "rationale": "Prevents degradation of insight quality over time",   "priority": "Medium"},
        {"action": "Set up monitoring for outlier conditions", "rationale": "Early warning system for anomalies in key metrics",   "priority": "Medium"},
    ]
}

FALLBACK_WHATIF = (
    "Based on this scenario simulation, adjusting the selected metric would shift your overall "
    "risk profile. The change propagates through the scoring formula, primarily affecting the "
    "trend stability and risk inverse components. Consider whether this scenario represents a "
    "realistic near-term possibility before making decisions based on it."
)


def _safe_json_parse(text: str, fallback: Any) -> Any:
    """Parse JSON from model output; strip markdown fences if present."""
    try:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)
    except Exception:
        return fallback


# ── Public API ────────────────────────────────────────────────────────────────

def generate_summary(profile: Dict[str, Any], dataset_context: str) -> Dict[str, Any]:
    """
    AI narrative summary + key findings.
    Sends only compact column stats — never raw data.
    """
    context_labels = {
        "business":       "business performance data (sales, revenue, expenses)",
        "personal_finance": "personal household budget and spending data",
        "student":        "student academic performance data (grades, attendance, study hours)",
        "civic":          "civic and smart community data (sustainability, healthcare, mobility)",
    }
    context_desc = context_labels.get(dataset_context, "general data")

    col_info = [
        {
            "name":          c["name"],
            "type":          c["dtype"],
            "mean":          c.get("mean"),
            "nulls_pct":     c["nulls_pct"],
            "outlier_count": c.get("outlier_count", 0),
        }
        for c in profile["columns"][:12]   # cap at 12 cols to control tokens
    ]

    prompt = f"""You are a data analyst. Analyze this {context_desc} profile and write a concise executive summary.

Dataset profile:
- Rows: {profile['row_count']}
- Columns: {profile['column_count']}
- Overall quality: {profile['overall_quality_pct']}%
- Column stats: {json.dumps(col_info, indent=2)}

Return ONLY valid JSON — no markdown, no explanation outside the JSON:
{{
  "summary_text": "3-4 sentence executive summary describing what this data shows and its health",
  "key_findings": ["finding 1", "finding 2", "finding 3", "finding 4"]
}}"""

    try:
        text   = safe_generate(prompt, json_mode=True, max_tokens=800)
        result = _safe_json_parse(text, FALLBACK_SUMMARY)
        if not isinstance(result.get("key_findings"), list):
            result["key_findings"] = FALLBACK_SUMMARY["key_findings"]
        return result
    except GeminiFallbackError:
        return FALLBACK_SUMMARY


def generate_opportunity_score(profile: Dict[str, Any], dataset_context: str) -> float:
    """
    Opportunity sub-score (0–100) — the ONLY AI-derived sub-score.
    Weight capped at 0.15 in the Decision Score formula.
    """
    context_labels = {
        "business":       "business",
        "personal_finance": "personal finance",
        "student":        "academic",
        "civic":          "civic and smart community",
    }
    ctx = context_labels.get(dataset_context, "general")

    numeric_cols = [
        {"name": c["name"], "mean": c.get("mean"), "std": c.get("std"),
         "min": c.get("min"), "max": c.get("max")}
        for c in profile["columns"] if c.get("mean") is not None
    ][:8]   # cap at 8 cols

    prompt = f"""You are a {ctx} data analyst. Estimate an Opportunity Score (0–100) for this dataset.

Scoring rubric:
  0–30:  Very limited opportunity / poor signals
  30–60: Moderate opportunity, some positive signals
  60–80: Good opportunity, clear growth/improvement potential
  80–100: Excellent opportunity, strong positive signals

Dataset: {profile['row_count']} rows, quality {profile['overall_quality_pct']}%
Key numeric columns: {json.dumps(numeric_cols, indent=2)}

Return ONLY valid JSON: {{"opportunity_score": <integer 0-100>}}"""

    try:
        text   = safe_generate(prompt, json_mode=True, max_tokens=80)
        result = _safe_json_parse(text, {"opportunity_score": FALLBACK_OPPORTUNITY})
        return max(0.0, min(100.0, float(result.get("opportunity_score", FALLBACK_OPPORTUNITY))))
    except GeminiFallbackError:
        return FALLBACK_OPPORTUNITY


def generate_recommendations(
    sub_scores: Dict[str, float],
    key_findings: List[str],
    dataset_context: str,
) -> Dict[str, Any]:
    """Top 3 priorities + recommended actions."""
    context_labels = {
        "business":       "business performance",
        "personal_finance": "personal financial health",
        "student":        "academic performance",
        "civic":          "civic and smart community health",
    }
    ctx = context_labels.get(dataset_context, "data")

    prompt = f"""You are a {ctx} advisor. Provide actionable recommendations based on this Decision Score analysis.

Sub-scores (0–100, higher is better):
  Data Quality:    {sub_scores['data_quality']:.1f}
  Trend Stability: {sub_scores['trend_stability']:.1f}
  Risk Inverse:    {sub_scores['risk_inverse']:.1f}
  Opportunity:     {sub_scores['opportunity']:.1f}

Key findings: {json.dumps(key_findings)}

Return ONLY valid JSON:
{{
  "top_priorities": [
    {{"text": "concise priority title", "rationale": "why this matters most", "impact_tag": "High Impact|Medium Impact|Quick Win"}},
    {{"text": "...", "rationale": "...", "impact_tag": "..."}},
    {{"text": "...", "rationale": "...", "impact_tag": "..."}}
  ],
  "recommendations": [
    {{"action": "specific action to take", "rationale": "short explanation", "priority": "High|Medium|Low"}},
    {{"action": "...", "rationale": "...", "priority": "..."}},
    {{"action": "...", "rationale": "...", "priority": "..."}}
  ]
}}"""

    try:
        text   = safe_generate(prompt, json_mode=True, max_tokens=900)
        result = _safe_json_parse(text, FALLBACK_RECOMMENDATIONS)
        if not isinstance(result.get("top_priorities"), list) \
                or not isinstance(result.get("recommendations"), list):
            return FALLBACK_RECOMMENDATIONS
        return result
    except GeminiFallbackError:
        return FALLBACK_RECOMMENDATIONS


def generate_whatif_explanation(
    column: str,
    pct_change: float,
    old_score: Dict[str, Any],
    new_score: Dict[str, Any],
    dataset_context: str,
) -> str:
    """
    Plain-language explanation of a What-If delta.
    CRITICAL: Never uses "forecast" or "predict" — always "scenario simulation".
    """
    direction   = "increase" if pct_change > 0 else "decrease"
    score_delta = new_score["score"] - old_score["score"]
    risk_changed = old_score["risk_level"] != new_score["risk_level"]

    # Per-sub-score deltas (so the LLM can be specific about what moved)
    old_sub = old_score["sub_scores"]
    new_sub = new_score["sub_scores"]
    sub_deltas = {
        k: round(float(new_sub[k]) - float(old_sub[k]), 1)
        for k in old_sub
    }

    # If scenario_deltas is attached to the new score, surface the lever breakdown
    scenario = new_score.get("scenario_deltas", {}) or {}
    polarity = scenario.get("polarity", "neutral")
    opp_delta = scenario.get("opportunity_delta", 0)
    stab_pen = scenario.get("stability_penalty", 0)
    risk_pen = scenario.get("risk_penalty", 0)

    prompt = f"""You are a data analyst explaining a SCENARIO SIMULATION result (NOT a forecast or prediction).

Scenario applied: '{column}' adjusted by {pct_change:+.0f}% ({abs(pct_change):.0f}% {direction}).
Column polarity: {polarity} (positive = bigger-is-better, negative = smaller-is-better, neutral = unknown).

Before simulation — Score: {old_score['score']:.1f}  Risk: {old_score['risk_level']}
After  simulation — Score: {new_score['score']:.1f}  Risk: {new_score['risk_level']}
Net change: {score_delta:+.1f} points{f" | Risk level changed: {old_score['risk_level']} → {new_score['risk_level']}" if risk_changed else ""}

Sub-score changes:
  - Data Quality:    {old_sub['data_quality']:.1f} → {new_sub['data_quality']:.1f}  (Δ {sub_deltas['data_quality']:+.1f})
  - Trend Stability: {old_sub['trend_stability']:.1f} → {new_sub['trend_stability']:.1f}  (Δ {sub_deltas['trend_stability']:+.1f})
  - Risk Inverse:    {old_sub['risk_inverse']:.1f} → {new_sub['risk_inverse']:.1f}  (Δ {sub_deltas['risk_inverse']:+.1f})
  - Opportunity:     {old_sub['opportunity']:.1f} → {new_sub['opportunity']:.1f}  (Δ {sub_deltas['opportunity']:+.1f})

Lever breakdown:
  - Opportunity delta: {opp_delta:+.1f}  (direction-aware, from column polarity)
  - Stability penalty: -{stab_pen:.1f}   (any artificial shift reduces trend stability)
  - Risk penalty:      -{risk_pen:.1f}   (only applied on adverse-direction moves)

Write exactly 2–3 plain sentences explaining what this scenario simulation shows and what the user should consider.
Rules:
  - NEVER use the words "forecast", "predict", or "prediction"
  - ALWAYS use "scenario simulation" or "trend projection"
  - Be specific about which sub-scores drove the change (cite the actual deltas above)
  - Be concise and actionable

Return plain text only — no JSON, no bullet points, no headers."""

    try:
        text = safe_generate(prompt, json_mode=False, max_tokens=250, use_cache=False)
        return text.strip() if text else FALLBACK_WHATIF
    except GeminiFallbackError:
        return FALLBACK_WHATIF


def generate_chat_response(
    message: str,
    history: List[Dict[str, str]],
    profile: Dict[str, Any],
    dataset_context: str,
) -> Dict[str, Any]:
    """
    P1: Dataset-aware Q&A via Gemini.
    Only profiling stats are sent — raw data never leaves the server.
    """
    col_names  = [c["name"] for c in profile["columns"]]
    col_stats  = [
        {"name": c["name"], "mean": c.get("mean"), "nulls_pct": c["nulls_pct"]}
        for c in profile["columns"][:10]
    ]
    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in history[-5:]
    )

    prompt = f"""You are a data analyst assistant for a {dataset_context} dataset.
Dataset: {profile['row_count']} rows, {profile['column_count']} columns.
Columns available: {', '.join(col_names)}
Column stats: {json.dumps(col_stats)}

Recent conversation:
{history_text}

User question: {message}

Answer concisely and specifically. Reference column names when relevant.
Return ONLY valid JSON: {{"reply": "your answer", "referenced_columns": ["col1", "col2"]}}"""

    try:
        text   = safe_generate(prompt, json_mode=True, max_tokens=400, use_cache=False)
        result = _safe_json_parse(text, {"reply": "Could not process that question.", "referenced_columns": []})
        return result
    except GeminiFallbackError:
        return {"reply": "Chat is temporarily unavailable. Please try again shortly.", "referenced_columns": []}
