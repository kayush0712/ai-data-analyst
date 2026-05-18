import pandas as pd


def _resolve_column(df, column):
    if column in df.columns:
        return column

    column_lower = column.lower().strip()

    for col in df.columns:
        if col.lower() == column_lower:
            return col

    for col in df.columns:
        if column_lower in col.lower():
            return col

    return None


def apply_filters(df, filters):
    if not filters:
        return df

    result = df.copy()

    for item in filters:
        column = _resolve_column(
            result,
            item.get("column", "")
        )

        if not column:
            continue

        operator = (
            item.get("operator")
            or item.get("op")
            or "eq"
        ).lower()

        value = item.get("value")

        series = result[column]

        if operator == "eq":
            mask = series.astype(str).str.lower() == str(value).lower()

        elif operator == "ne":
            mask = series.astype(str).str.lower() != str(value).lower()

        elif operator == "contains":
            mask = (
                series.astype(str)
                .str.lower()
                .str.contains(
                    str(value).lower(),
                    na=False
                )
            )

        elif operator == "gt":
            mask = pd.to_numeric(series, errors="coerce") > float(value)

        elif operator == "gte":
            mask = pd.to_numeric(series, errors="coerce") >= float(value)

        elif operator == "lt":
            mask = pd.to_numeric(series, errors="coerce") < float(value)

        elif operator == "lte":
            mask = pd.to_numeric(series, errors="coerce") <= float(value)

        elif operator == "is_null":
            mask = series.isna()

        else:
            continue

        result = result[mask]

    return result
