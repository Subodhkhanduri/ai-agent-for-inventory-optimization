import pandas as pd
import numpy as np

REQUIRED_COLUMNS = ["Date", "Demand", "Item", "Store"]

class DataValidator:

    def validate(self, df: pd.DataFrame):
        issues = []

        # -------- A. Required columns --------
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                issues.append(f"❌ Missing required column: {col}")

        # If required columns missing → immediate failure
        hard_errors = [msg for msg in issues if msg.startswith("❌")]
        if hard_errors:
            return False, hard_errors

        # -------- B. Datatype checks --------
        try:
            df["Date"] = pd.to_datetime(df["Date"])
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Date parsing failed: {e}")
            issues.append("❌ Date column contains invalid date format")

        for col in ["Demand", "Item", "Store"]:
            if not pd.api.types.is_numeric_dtype(df[col]):
                issues.append(f"❌ Column '{col}' must be numeric")

        # -------- C. Missing values --------
        if df[REQUIRED_COLUMNS].isnull().any().any():
            issues.append("❌ Dataset contains missing values in required fields")

        # -------- D. Duplicate detection --------
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            issues.append(f"⚠ {duplicates} duplicate rows found")

        # -------- E. Outlier detection (IQR) --------
        q1 = df["Demand"].quantile(0.25)
        q3 = df["Demand"].quantile(0.75)
        iqr = q3 - q1

        outliers = ((df["Demand"] < (q1 - 1.5 * iqr)) |
                    (df["Demand"] > (q3 + 1.5 * iqr))).sum()

        if outliers > 0:
            issues.append(f"⚠ {outliers} potential outliers detected in Demand")

        # -------------------------------
        # CLASSIFY ISSUES
        # -------------------------------
        hard_errors = [msg for msg in issues if msg.startswith("❌")]
        soft_warnings = [msg for msg in issues if msg.startswith("⚠")]

        # If hard errors exist → fail
        if hard_errors:
            return False, hard_errors + soft_warnings

        # No hard errors → PASS even with warnings
        return True, ["Validation passed"] + soft_warnings
