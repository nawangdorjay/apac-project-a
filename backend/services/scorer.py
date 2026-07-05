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
    """
    numeric_cols = profile.get("numeric_cols", [])
    columns = profile.get("columns", [])
    row_count = profile.get("row_count", 0)

    # --- 1. Data Quality Score (0-100) ---
    # Completeness (% non-null), type conformity, outlier ratio
    completeness = (1 - _get_avg_null_pct(columns) / 100)
    
    total_outliers = sum(c.get("outlier_count", 0) for c in columns)
    total_numeric_vals = sum(
        df[col].count() for col in numeric_cols if col in df.columns
    ) if numeric_cols else 1
    outlier_ratio = total_outliers / max(total_numeric_vals, 1)
    
    # Type conformity: fraction of cols that have consistent types (no mixed)
    type_conformity = _compute_type_conformity(df, columns)
    
    data_quality_score = (
        completeness * 50 +           # 50% weight on completeness
        type_conformity * 30 +        # 30% weight on type conformity
        (1 - min(outlier_ratio * 3, 1)) * 20  # 20% weight on low outlier ratio
    )
    data_quality_score = max(0.0, min(100.0, data_quality_score))

    # --- 2. Trend Stability Score (0-100) ---
    # Lower coefficient of variation across numeric cols = higher stability
    if numeric_cols:
        cvs = []
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
    else:
        trend_stability_score = 50.0

    # --- 3. Risk Inverse Score (0-100) ---
    # More anomalies = lower score
    # Based on: outlier density + null density
    null_density = _get_avg_null_pct(columns) / 100
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

    # --- AI Confidence (from data sufficiency, never from model self-report) ---
    # Based on: row count (more = better), completeness, variance
    row_score = min(row_count / 100, 1.0)  # 100+ rows = full confidence on this factor
    completeness_score = completeness
    variance_score = 1.0 - min(np.mean([
        df[col].std() / (abs(df[col].mean()) + 1e-9)
        for col in numeric_cols if col in df.columns
    ]) / 2.0, 1.0) if numeric_cols else 0.5

    confidence = round((row_score * 0.4 + completeness_score * 0.4 + variance_score * 0.2) * 100, 1)
    confidence = max(10.0, min(98.0, confidence))

    return {
        "score": decision_score,
        "risk_level": risk_level,
        "confidence": confidence,
        "sub_scores": {
            "data_quality": round(data_quality_score, 1),
            "trend_stability": round(trend_stability_score, 1),
            "risk_inverse": round(risk_inverse_score, 1),
            "opportunity": round(opportunity_score, 1)
        }
    }


POSITIVE_COLUMNS = {
    # Business
    "revenue", "profit", "units_sold", "customer_satisfaction", "customers",
    # Personal Finance
    "income", "savings",
    # Smart Communities
    "public_transit_ridership", "waste_recycled_tons", "green_space_visitors"
}

NEGATIVE_COLUMNS = {
    # Business
    "expenses", "returns", "marketing_spend",
    # Personal Finance
    "housing", "food_groceries", "dining_out", "transport", "entertainment", "utilities", "healthcare", "subscriptions",
    # Smart Communities
    "air_quality_index", "traffic_delay_pct", "streetlight_outages", "citizen_service_requests", "water_consumption_m_liters"
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
    Applies performance impact deltas (positive/negative impact based on column polarity)
    so the simulator reacts dynamically and realistically.
    """
    df_perturbed = df.copy()
    if column in df_perturbed.columns:
        df_perturbed[column] = df_perturbed[column] * (1 + pct_change / 100)
    
    # Rebuild profile for perturbed data
    from services.profiler import profile_dataframe
    perturbed_profile = profile_dataframe(df_perturbed)
    
    res = compute_decision_score(df_perturbed, perturbed_profile, original_opportunity_score)
    
    # Calculate performance impact delta based on column polarity
    col_lower = column.lower().replace(" ", "_")
    impact_delta = 0.0
    if col_lower in POSITIVE_COLUMNS:
        # Higher positive column = better score
        impact_delta = (pct_change / 100.0) * 15.0
    elif col_lower in NEGATIVE_COLUMNS:
        # Higher negative column = worse score
        impact_delta = -(pct_change / 100.0) * 15.0
        
    if impact_delta != 0.0:
        res["score"] = round(max(0.0, min(100.0, res["score"] + impact_delta)), 1)
        
        # Adjust sub-scores dynamically to reflect the value change
        if impact_delta > 0:
            res["sub_scores"]["trend_stability"] = round(max(0.0, min(100.0, res["sub_scores"]["trend_stability"] + impact_delta)), 1)
        else:
            res["sub_scores"]["risk_inverse"] = round(max(0.0, min(100.0, res["sub_scores"]["risk_inverse"] + impact_delta)), 1)
            
        # Re-bucket Risk Level
        if res["score"] >= 75:
            res["risk_level"] = "Low"
        elif res["score"] >= 50:
            res["risk_level"] = "Medium"
        else:
            res["risk_level"] = "High"
            
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
    Generate a simple outcome projection (linear trend) for a numeric column.
    Returns:
      - historical: list of values
      - projected: list of predicted values (including standard error bounds)
      - message: string detailing the trend direction
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
