import re

import pandas as pd

from helpers.dtype_helper import prepare_dataframe


def _resolve_column(df, token):
    if not token:
        return None

    token_lower = token.lower().strip().replace(" ", "_")

    if token in df.columns:
        return token

    for col in df.columns:
        if col.lower() == token_lower:
            return col

    for col in df.columns:
        col_norm = col.lower().replace("_", " ")

        if token_lower in col_norm.replace(" ", "_"):
            return col

        if token_lower in col_norm:
            return col

    return None


def _is_numeric_column(df, col):
    prepared = prepare_dataframe(
        df[[col]].copy()
    )
    return pd.api.types.is_numeric_dtype(
        prepared[col]
    )


def _columns_mentioned_in_question(df, question_lower):
    matched = []

    for col in df.columns:
        col_lower = col.lower()
        col_spaced = col_lower.replace("_", " ")

        if col_lower in question_lower:
            matched.append(col)
            continue

        if col_spaced in question_lower:
            matched.append(col)
            continue

        for part in col_spaced.split():
            if len(part) >= 4 and part in question_lower:
                matched.append(col)
                break

    explicit_patterns = [
        r"chart\s+of\s+([a-zA-Z_ ]+?)(?:\s+by|\s+vs|\s*$|,)",
        r"graph\s+of\s+([a-zA-Z_ ]+?)(?:\s+by|\s+vs|\s*$|,)",
        r"plot\s+of\s+([a-zA-Z_ ]+?)(?:\s+by|\s+vs|\s*$|,)",
        r"plot\s+([a-zA-Z_ ]+?)(?:\s+by|\s+vs|\s*$|,)",
        r"visuali[sz]e\s+([a-zA-Z_ ]+?)(?:\s+by|\s+vs|\s*$|,)",
        r"make\s+(?:a\s+)?chart\s+of\s+([a-zA-Z_ ]+?)(?:\s+by|\s+vs|\s*$|,)",
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, question_lower)

        if match:
            col = _resolve_column(
                df,
                match.group(1).strip(),
            )

            if col and col not in matched:
                matched.insert(0, col)

    return matched


def parse_chart_columns(df, question):
    plot_df = prepare_dataframe(df.copy())
    question_lower = question.lower().strip()

    x_col = None
    y_col = None

    vs_match = re.search(
        r"([a-zA-Z_ ]+?)\s+vs\.?\s+([a-zA-Z_ ]+)",
        question_lower,
    )

    by_match = re.search(
        r"([a-zA-Z_ ]+?)\s+by\s+([a-zA-Z_ ]+)",
        question_lower,
    )

    if vs_match:
        left = _resolve_column(df, vs_match.group(1).strip())
        right = _resolve_column(df, vs_match.group(2).strip())

        if left and right:
            if _is_numeric_column(plot_df, right):
                x_col, y_col = left, right
            elif _is_numeric_column(plot_df, left):
                x_col, y_col = right, left
            else:
                x_col, y_col = left, right

    elif by_match:
        value_col = _resolve_column(
            df,
            by_match.group(1).strip(),
        )
        group_col = _resolve_column(
            df,
            by_match.group(2).strip(),
        )

        if value_col and group_col:
            x_col = group_col
            y_col = value_col

    mentioned = _columns_mentioned_in_question(
        df,
        question_lower,
    )

    if mentioned and not y_col:
        numeric = [
            col for col in mentioned
            if _is_numeric_column(plot_df, col)
        ]
        categorical = [
            col for col in mentioned
            if col not in numeric
        ]

        if len(mentioned) == 1:
            col = mentioned[0]

            if _is_numeric_column(plot_df, col):
                y_col = col
            else:
                x_col = col

        elif numeric and categorical:
            y_col = numeric[0]
            x_col = categorical[0]

        elif len(numeric) >= 2:
            x_col = numeric[0]
            y_col = numeric[1]

        elif len(numeric) == 1:
            y_col = numeric[0]

        elif len(categorical) == 1:
            x_col = categorical[0]

    return x_col, y_col
