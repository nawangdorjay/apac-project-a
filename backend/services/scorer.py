import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def compute_decision_score(
    df: pd.DataFrame,
    profile: Dict[str, Any],
    opportunity_score: float = 50.0
) -> Dict[str, Any]:
    """
    Compute the Decision Score using the exact weighted formula from the PRD.

    Decision Score = (0.35 × Data Quality Score)
                   + (0.25 × Trend Stability Score)
                   + (0.25 × Risk Inverse Score)
                   + (0.15 × Opportunity Score)

    All sub-scores except Opportunity are 100% deterministic.

    Confidence is a SEPARATE metric (not the score) that quantifies how
    much we should trust the score. It uses three DIVERSIFIED signals:
      - Sample size sufficiency (40%): more rows = more trust
      - Completeness (40%): fewer nulls = more trust
      - Column coverage (20%): more numeric columns × rows-per-column
        = more statistical power. This is INTENTIONALLY different from
        trend_stability (which uses coefficient of variation) so the
        two metrics don't move in lockstep.
    """
    numeric_cols = profile.get("numeric_cols", [])
    columns = profile.get("columns", [])
    row_count = profile.get("row_count", 0)

    # --- 1. Data Quality Score (0-100) ---
    # Completeness (% non-null), type conformity, outlier ratio
    avg_null_pct = _get_avg_null_pct(columns)
    completeness = (1 - avg_null_pct / 100)

    total_outliers = sum(c.get("outlier_count", 0) for c in columns)
    total_numeric_vals = sum(
        df[col].count() for col in numeric_cols if col in df.columns
    ) if numeric_cols else 1
    outlier_ratio = total_outliers / max(total_numeric_vals, 1)

    # Type conformity: fraction of cols that have consistent types (no mixed)
    type_conformity = _compute_type_conformity(df, columns)

    # Outlier component (low outlier ratio = high score)
    outlier_component = 1 - min(outlier_ratio * 3, 1)

    data_quality_score = (
        completeness * 50 +           # 50% weight on completeness
        type_conformity * 30 +        # 30% weight on type conformity
        outlier_component * 20        # 20% weight on low outlier ratio
    )
    data_quality_score = max(0.0, min(100.0, data_quality_score))

    # --- 2. Trend Stability Score (0-100) ---
    # Lower coefficient of variation across numeric cols = higher stability
    cvs = []
    if numeric_cols:
        for col in numeric_cols:
            if col in df.columns:
                col_data = df[col].dropna()
                if len(col_data) > 1 and col_data.mean() != 0:
                    cv = col_data.std() / abs(col_data.mean())
                    cvs.append(min(cv, 2.0))  # cap CV at 2.0
    if cvs:
        avg_cv = np.mean(cvs)
        trend_stability_score = max(0.0, (1 - avg_cv / 2.0) * 100)
    else:
        trend_stability_score = 50.0

    # --- 3. Risk Inverse Score (0-100) ---
    # More anomalies = lower score
    # Based on: outlier density + null density
    null_density = avg_null_pct / 100
    anomaly_density = min((outlier_ratio + null_density) / 2, 1.0)
    risk_inverse_score = max(0.0, (1 - anomaly_density) * 100)

    # --- 4. Opportunity Score (0-100) ---
    # Gemini-assisted (passed in as parameter, capped weight at 0.15)
    opportunity_score = max(0.0, min(100.0, opportunity_score))

    # --- Final Weighted Score ---
    decision_score = (
        0.35 * data_quality_score +
        0.25 * trend_stability_score +
        0.25 * risk_inverse_score +
        0.15 * opportunity_score
    )
    decision_score = round(max(0.0, min(100.0, decision_score)), 1)

    # --- Risk Level (deterministic bucket) ---
    if decision_score >= 75:
        risk_level = "Low"
    elif decision_score >= 50:
        risk_level = "Medium"
    else:
        risk_level = "High"

    # --- AI Confidence (DIVERSIFIED — no longer redundant with trend_stability) ---
    # Three signals, each measuring a DIFFERENT dimension of trust:
    #   1. Sample size sufficiency (40%): sqrt-saturating curve so 100+ rows = full
    #   2. Completeness (40%): same metric as data_quality, but weighted differently
    #   3. Column coverage (20%): statistical power = numeric_cols × rows_per_col
    #      This is NOT CV-based, so confidence and trend_stability can move independently.
    row_score = min(np.sqrt(row_count / 100), 1.0) if row_count > 0 else 0.0
    completeness_score = completeness  # 0-1
    # Effective sample size: numeric_cols × rows, normalized to a target of 200
    # (e.g. 10 cols × 20 rows = 200 → full coverage; 2 cols × 5 rows = 10 → low)
    eff_n = len(numeric_cols) * row_count
    coverage_score = min(eff_n / 200.0, 1.0) if eff_n > 0 else 0.0

    confidence = round((row_score * 0.4 + completeness_score * 0.4 + coverage_score * 0.2) * 100, 1)
    confidence = max(10.0, min(98.0, confidence))

    # --- Per-sub-score explanation breakdown (for the Score Breakdown Math modal) ---
    sub_score_explanations = {
        "data_quality": {
            "score": round(data_quality_score, 1),
            "weight": 0.35,
            "contribution": round(0.35 * data_quality_score, 1),
            "formula": "0.50 × Completeness + 0.30 × TypeConformity + 0.20 × (1 − OutlierRatio×3)",
            "components": {
                "completeness": {
                    "value": round(completeness, 4),
                    "raw": f"1 − ({avg_null_pct:.2f}% / 100) = {completeness:.4f}",
                    "weight": 0.50,
                    "label": "Completeness (non-null %)",
                },
                "type_conformity": {
                    "value": round(type_conformity, 4),
                    "raw": f"{int(type_conformity * len(columns))} / {len(columns)} columns consistently typed",
                    "weight": 0.30,
                    "label": "Type Conformity",
                },
                "outlier_component": {
                    "value": round(outlier_component, 4),
                    "raw": f"1 − min({outlier_ratio:.4f} × 3, 1) = {outlier_component:.4f}  ({total_outliers} outliers / {total_numeric_vals} numeric values)",
                    "weight": 0.20,
                    "label": "Outlier Inverse",
                },
            },
        },
        "trend_stability": {
            "score": round(trend_stability_score, 1),
            "weight": 0.25,
            "contribution": round(0.25 * trend_stability_score, 1),
            "formula": "(1 − avgCV / 2.0) × 100   where avgCV = mean(std / |mean|) per numeric column",
            "components": {
                "avg_cv": {
                    "value": round(float(np.mean(cvs)), 4) if cvs else None,
                    "raw": f"mean of CVs across {len(cvs)} numeric cols = {float(np.mean(cvs)):.4f}" if cvs else "no numeric cols with non-zero mean",
                    "weight": None,
                    "label": "Average Coefficient of Variation",
                },
                "capped_cvs": {
                    "value": len(cvs),
                    "raw": f"{len(cvs)} cols (CV capped at 2.0)",
                    "weight": None,
                    "label": "Cols included",
                },
            },
        },
        "risk_inverse": {
            "score": round(risk_inverse_score, 1),
            "weight": 0.25,
            "contribution": round(0.25 * risk_inverse_score, 1),
            "formula": "(1 − anomaly_density) × 100   where anomaly_density = (outlier_ratio + null_density) / 2",
            "components": {
                "outlier_ratio": {
                    "value": round(outlier_ratio, 4),
                    "raw": f"{total_outliers} outliers / {total_numeric_vals} numeric values = {outlier_ratio:.4f}",
                    "weight": 0.5,
                    "label": "Outlier Ratio",
                },
                "null_density": {
                    "value": round(null_density, 4),
                    "raw": f"avg nulls_pct / 100 = {null_density:.4f}",
                    "weight": 0.5,
                    "label": "Null Density",
                },
                "anomaly_density": {
                    "value": round(anomaly_density, 4),
                    "raw": f"({outlier_ratio:.4f} + {null_density:.4f}) / 2 = {anomaly_density:.4f}",
                    "weight": None,
                    "label": "Anomaly Density (combined)",
                },
            },
        },
        "opportunity": {
            "score": round(opportunity_score, 1),
            "weight": 0.15,
            "contribution": round(0.15 * opportunity_score, 1),
            "formula": "Gemini-derived 0–100 score (capped weight to prevent AI bias)",
            "components": {
                "source": {
                    "value": opportunity_score,
                    "raw": "Google Gemini 2.0 Flash evaluates dataset profile (rows, columns, quality, numeric stats) and returns 0–100",
                    "weight": None,
                    "label": "AI-derived (Gemini 2.0 Flash)",
                },
            },
        },
        "confidence": {
            "score": round(confidence, 1),
            "weight": None,  # confidence is separate from the score
            "contribution": None,
            "formula": "0.40 × SampleSize + 0.40 × Completeness + 0.20 × ColumnCoverage   (NOT used in Decision Score — separate trust metric)",
            "components": {
                "sample_size": {
                    "value": round(float(row_score), 4),
                    "raw": f"sqrt({row_count} / 100) = {row_score:.4f}",
                    "weight": 0.40,
                    "label": "Sample Size (sqrt-saturating)",
                },
                "completeness": {
                    "value": round(float(completeness_score), 4),
                    "raw": f"1 − ({avg_null_pct:.2f}% / 100) = {completeness_score:.4f}",
                    "weight": 0.40,
                    "label": "Completeness",
                },
                "column_coverage": {
                    "value": round(float(coverage_score), 4),
                    "raw": f"({len(numeric_cols)} cols × {row_count} rows) / 200 = {coverage_score:.4f}",
                    "weight": 0.20,
                    "label": "Column Coverage (statistical power)",
                },
            },
        },
    }

    return {
        "score": decision_score,
        "risk_level": risk_level,
        "confidence": confidence,
        "sub_scores": {
            "data_quality": round(data_quality_score, 1),
            "trend_stability": round(trend_stability_score, 1),
            "risk_inverse": round(risk_inverse_score, 1),
            "opportunity": round(opportunity_score, 1)
        },
        "sub_score_explanations": sub_score_explanations,
        "score_formula": {
            "formula": "0.35 × DataQuality + 0.25 × TrendStability + 0.25 × RiskInverse + 0.15 × Opportunity",
            "weights": {"data_quality": 0.35, "trend_stability": 0.25, "risk_inverse": 0.25, "opportunity": 0.15},
            "computation": f"0.35 × {data_quality_score:.1f} + 0.25 × {trend_stability_score:.1f} + 0.25 × {risk_inverse_score:.1f} + 0.15 × {opportunity_score:.1f} = {decision_score:.1f}",
        }
    }


POSITIVE_COLUMNS = {
    # Business
    "revenue", "profit", "units_sold", "customer_satisfaction", "customers",
    # Personal Finance
    "income", "savings",
    # Smart Communities
    "public_transit_ridership", "waste_recycled_tons", "green_space_visitors",
    # Healthcare Wellness
    "population", "clinics_within_5km", "preventive_visit_pct", "telehealth_pct", "insurance_coverage_pct",
    # Student
    "attendance_pct", "study_hours", "sleep_hours", "final_score", "gpa"
}

NEGATIVE_COLUMNS = {
    # Business
    "expenses", "returns", "marketing_spend",
    # Personal Finance
    "housing", "food_groceries", "dining_out", "transport", "entertainment", "utilities", "healthcare", "subscriptions",
    # Smart Communities
    "air_quality_index", "traffic_delay_pct", "streetlight_outages", "citizen_service_requests", "water_consumption_m_liters",
    # Healthcare Wellness
    "avg_wait_minutes", "emergency_visits", "chronic_disease_pct", "senior_pop_pct",
    # Student
    "screentime_hours", "absences"
}

def perturb_and_rescore(
    df: pd.DataFrame,
    profile: Dict[str, Any],
    column: str,
    pct_change: float,
    original_opportunity_score: float = 50.0
) -> Dict[str, Any]:
    """
    What-If: perturb a column by pct_change% and recompute the Decision Score.

    The scorer is intentionally scale-invariant in some dimensions (CV, IQR),
    so we also inject a small set of **scenario-aware perturbation deltas**
    to make the simulator respond visibly to user input:

      - Opportunity sub-score  : direction-aware delta from column polarity
                                 (positive columns up = good, negative columns up = bad).
                                 Multiplier raised from 1.3 → 1.6 so a +30% shift
                                 on a positive column moves Opportunity by ~+24
                                 points (which translates to ~+3.6 on the final
                                 score via the 0.15 weight).

      - Trend Stability penalty : any artificial shift represents a deviation from
                                 the historical pattern. We subtract a small
                                 penalty proportional to |pct_change|, capped at
                                 20 points for extreme ±50% scenarios. This makes
                                 "no change" the highest-stability baseline and
                                 larger moves cost stability.

      - Risk Inverse penalty    : for positive columns, a decrease raises risk
                                 (downside exposure). For negative columns, an
                                 increase raises risk. Symmetric, capped at 15
                                 points. No penalty for moves in the favorable
                                 direction (the scenario improves risk).

    These deltas are deterministic and labeled in `scenario_deltas` so the
    LLM explanation and the UI sub-score comparison can clearly show *which*
    lever moved and why.
    """
    df_perturbed = df.copy()
    if column in df_perturbed.columns:
        df_perturbed[column] = df_perturbed[column] * (1 + pct_change / 100)

    # Rebuild profile for perturbed data
    from services.profiler import profile_dataframe
    perturbed_profile = profile_dataframe(df_perturbed)

    # --- Column polarity lookup ---
    col_lower = column.lower().replace(" ", "_")
    is_positive = col_lower in POSITIVE_COLUMNS
    is_negative = col_lower in NEGATIVE_COLUMNS
    # Polarity sign: +1 means "bigger is better", -1 means "smaller is better"
    polarity = 1 if is_positive else (-1 if is_negative else 0)

    # --- 1. Opportunity delta (directional) ---
    # multiplier raised to 1.6 (was 1.3) so the slider feels responsive
    opportunity_delta = 0.0
    if polarity != 0:
        opportunity_delta = polarity * pct_change * 1.6
    new_opportunity = max(0.0, min(100.0, original_opportunity_score + opportunity_delta))

    # --- 2. Trend Stability penalty (any shift = deviation from history) ---
    # Linear in |pct_change|, capped at 20 points for ±50%.
    stability_penalty = min(abs(pct_change) * 0.4, 20.0)

    # --- 3. Risk Inverse penalty (directional, only penalize adverse moves) ---
    # polarity * sign(pct_change) > 0 means favorable direction → no penalty
    # polarity * sign(pct_change) < 0 means adverse direction → penalty
    risk_penalty = 0.0
    if polarity != 0 and pct_change != 0:
        direction = 1 if pct_change > 0 else -1
        if polarity * direction < 0:
            # adverse move
            risk_penalty = min(abs(pct_change) * 0.3, 15.0)

    # Compute the score with the perturbed df + new opportunity,
    # then apply stability and risk penalties.
    res = compute_decision_score(df_perturbed, perturbed_profile, new_opportunity)

    # Apply penalties to sub-scores (clamped to [0, 100])
    res["sub_scores"]["trend_stability"] = round(max(0.0, min(100.0,
        res["sub_scores"]["trend_stability"] - stability_penalty)), 1)
    res["sub_scores"]["risk_inverse"] = round(max(0.0, min(100.0,
        res["sub_scores"]["risk_inverse"] - risk_penalty)), 1)

    # Recompute the weighted Decision Score from the adjusted sub-scores
    adjusted_score = (
        0.35 * res["sub_scores"]["data_quality"] +
        0.25 * res["sub_scores"]["trend_stability"] +
        0.25 * res["sub_scores"]["risk_inverse"] +
        0.15 * res["sub_scores"]["opportunity"]
    )
    res["score"] = round(max(0.0, min(100.0, adjusted_score)), 1)

    # Re-bucket risk level
    if res["score"] >= 75:
        res["risk_level"] = "Low"
    elif res["score"] >= 50:
        res["risk_level"] = "Medium"
    else:
        res["risk_level"] = "High"

    # Attach a transparent scenario-delta breakdown for the UI / LLM explanation
    res["scenario_deltas"] = {
        "column": column,
        "polarity": "positive" if polarity > 0 else "negative" if polarity < 0 else "neutral",
        "pct_change": pct_change,
        "opportunity_delta": round(opportunity_delta, 1),
        "stability_penalty": round(stability_penalty, 1),
        "risk_penalty": round(risk_penalty, 1),
        "original_opportunity": round(float(original_opportunity_score), 1),
        "new_opportunity": round(float(new_opportunity), 1),
    }

    return res


# --- Helpers ---

def _get_avg_null_pct(columns: list) -> float:
    if not columns:
        return 0.0
    return np.mean([c.get("nulls_pct", 0) for c in columns])


def _compute_type_conformity(df: pd.DataFrame, columns: list) -> float:
    """Fraction of columns that are consistently typed (not mixed)."""
    if not columns:
        return 1.0
    consistent = 0
    for col in columns:
        col_name = col["name"]
        if col_name not in df.columns:
            continue
        col_data = df[col_name].dropna()
        if len(col_data) == 0:
            consistent += 1
            continue
        # Check if all values are same type
        types = set(type(v).__name__ for v in col_data.head(50))
        if len(types) <= 1:
            consistent += 1
        elif types <= {"int", "float", "int64", "float64"}:
            consistent += 1  # Mixed int/float is fine
    return consistent / len(columns)


def forecast_series(df: pd.DataFrame, column: str, periods: int = 3) -> Dict[str, Any]:
    """
    Generate a simple linear trend projection (least-squares fit) for a
    numeric column. Returns:
      - historical: list of {index, value} points
      - projected:  list of {index, value, lower, upper} points where
                    lower/upper form a 95% CI band based on residual std
      - message:    string detailing the trend direction

    NOTE: This is a naive extrapolation — not an ML forecast. It assumes
    the historical linear trend continues unchanged. Useful for sanity-
    checking momentum, not for predicting shocks or seasonality.
    """
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return {"historical": [], "projected": [], "message": "Non-numeric column"}
    
    series = df[column].dropna().tolist()
    if len(series) < 3:
        return {"historical": series, "projected": [], "message": "Not enough historical data points for projection"}
        
    y = np.array(series)
    x = np.arange(len(y))
    
    # Fit linear line y = mx + c
    slope, intercept = np.polyfit(x, y, 1)
    
    # Compute residuals & standard error for confidence intervals
    preds = slope * x + intercept
    residuals = y - preds
    std_err = np.std(residuals) if len(residuals) > 1 else 0.0
    
    historical_points = [{"index": int(i), "value": float(val)} for i, val in enumerate(series)]
    projected_points = []
    
    for step in range(1, periods + 1):
        idx = len(series) - 1 + step
        pred_val = slope * idx + intercept
        projected_points.append({
            "index": int(idx),
            "value": float(round(pred_val, 2)),
            "lower": float(round(pred_val - 1.96 * std_err, 2)),
            "upper": float(round(pred_val + 1.96 * std_err, 2))
        })
        
    trend_dir = "upward" if slope > 0 else "downward" if slope < 0 else "stable"
    message = f"Based on linear trend projection, '{column}' exhibits a {trend_dir} trajectory (slope: {slope:.3f})."
    
    return {
        "historical": historical_points,
        "projected": projected_points,
        "message": message,
        "slope": float(slope),
        "std_err": float(std_err)
    }
