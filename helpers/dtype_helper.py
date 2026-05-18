import pandas as pd

NUMERIC_HINTS = (
    "salary", "experience", "age", "score",
    "amount", "price", "count", "year",
    "revenue", "cost", "total", "numeric",
    "performance", "rating", "percent",
)


def prepare_dataframe(df):
    result = df.copy()

    for col in result.columns:
        col_lower = col.lower().strip()

        if any(hint in col_lower for hint in NUMERIC_HINTS):
            converted = pd.to_numeric(
                result[col],
                errors="coerce",
            )

            if converted.notna().any():
                result[col] = converted

    return result
