import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
import io

def clean_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Clean a DataFrame: dedupe, handle nulls, fix types.
    Returns cleaned DataFrame and a log of changes made.
    """
    log = []
    rows_before = len(df)

    # 1. Remove duplicate rows
    dupe_count = df.duplicated().sum()
    if dupe_count > 0:
        df = df.drop_duplicates()
        log.append(f"Removed {dupe_count} duplicate row{'s' if dupe_count > 1 else ''}")

    # 2. Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        before = df[col].copy()
        df[col] = df[col].str.strip()
        changed = (before != df[col]).sum()
        if changed > 0:
            log.append(f"Stripped whitespace in '{col}' ({changed} cell{'s' if changed > 1 else ''})")

    # 3. Fix malformed dates — try converting object cols that look like dates
    for col in df.select_dtypes(include="object").columns:
        sample = df[col].dropna().head(10)
        try:
            converted = pd.to_datetime(sample, infer_datetime_format=True)
            # If at least 80% parse successfully, convert the whole column
            full_converted = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
            success_rate = full_converted.notna().mean()
            if success_rate >= 0.8:
                null_before = df[col].isna().sum()
                df[col] = full_converted
                null_after = df[col].isna().sum()
                newly_null = null_after - null_before
                log.append(f"Converted '{col}' to datetime{f' ({newly_null} malformed values set to null)' if newly_null > 0 else ''}")
        except Exception:
            pass

    # 4. Convert numeric strings to numbers
    for col in df.select_dtypes(include="object").columns:
        sample = df[col].dropna().head(20)
        try:
            # Try stripping common currency/percent symbols
            cleaned_sample = sample.str.replace(r"[$,%€£]", "", regex=True).str.strip()
            numeric_sample = pd.to_numeric(cleaned_sample, errors="coerce")
            if numeric_sample.notna().mean() >= 0.8:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(r"[$,%€£]", "", regex=True).str.strip(),
                    errors="coerce"
                )
                log.append(f"Converted '{col}' from text to numeric")
        except Exception:
            pass

    # 5. Handle null values
    null_summary = df.isnull().sum()
    null_cols = null_summary[null_summary > 0]
    for col, count in null_cols.items():
        pct = count / len(df) * 100
        if pct > 50:
            # More than 50% null — drop the column
            df = df.drop(columns=[col])
            log.append(f"Dropped column '{col}' ({pct:.0f}% null values)")
        elif df[col].dtype in [np.float64, np.int64, float, int] or pd.api.types.is_numeric_dtype(df[col]):
            # Fill numeric with median
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            log.append(f"Filled {count} null value{'s' if count > 1 else ''} in '{col}' with median ({median_val:.2f})")
        else:
            # Fill categorical with mode or 'Unknown'
            mode_vals = df[col].mode()
            fill_val = mode_vals[0] if len(mode_vals) > 0 else "Unknown"
            df[col] = df[col].fillna(fill_val)
            log.append(f"Filled {count} null value{'s' if count > 1 else ''} in '{col}' with '{fill_val}'")

    rows_after = len(df)
    if rows_after < rows_before:
        # Already logged dupes above, but capture if something else reduced rows
        pass

    if not log:
        log.append("Data is clean — no issues found")

    return df, log
