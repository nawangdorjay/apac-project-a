import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Comprehensive pandas-based profiling. 100% deterministic — no AI calls.
    Returns column profiles, correlations, and overall quality score.
    """
    columns = []
    numeric_cols = []

    for col in df.columns:
        col_data = df[col]
        dtype = str(col_data.dtype)
        nulls_pct = round(col_data.isna().mean() * 100, 2)
        unique_count = int(col_data.nunique())
        outlier_count = 0

        profile = {
            "name": col,
            "dtype": dtype,
            "nulls_pct": nulls_pct,
            "unique_count": unique_count,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
            "outlier_count": 0,
            "sample_values": col_data.dropna().head(5).tolist()
        }

        if pd.api.types.is_numeric_dtype(col_data):
            numeric_cols.append(col)
            clean = col_data.dropna()
            if len(clean) > 0:
                profile["min"] = round(float(clean.min()), 4)
                profile["max"] = round(float(clean.max()), 4)
                profile["mean"] = round(float(clean.mean()), 4)
                profile["std"] = round(float(clean.std()), 4) if len(clean) > 1 else 0.0

                # IQR outlier detection
                Q1 = clean.quantile(0.25)
                Q3 = clean.quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                outlier_count = int(((clean < lower) | (clean > upper)).sum())
                profile["outlier_count"] = outlier_count

        columns.append(profile)

    # Correlation matrix (numeric columns only)
    correlations = {}
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr().round(4)
        correlations = {
            col: {other: round(float(val), 4) for other, val in row.items()}
            for col, row in corr_matrix.to_dict().items()
        }

    # Overall quality score
    avg_completeness = (1 - df.isnull().mean().mean()) * 100
    total_outliers = sum(c["outlier_count"] for c in columns)
    total_numeric_vals = sum(df[col].count() for col in numeric_cols) if numeric_cols else 1
    outlier_ratio = total_outliers / max(total_numeric_vals, 1)
    overall_quality_pct = round(avg_completeness * (1 - outlier_ratio * 0.3), 2)
    overall_quality_pct = max(0.0, min(100.0, overall_quality_pct))

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "correlations": correlations,
        "overall_quality_pct": overall_quality_pct,
        "numeric_cols": numeric_cols
    }
