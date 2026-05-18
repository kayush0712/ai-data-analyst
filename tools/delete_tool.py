import pandas as pd

from tools.filters import apply_filters
from helpers.intent_parser import build_delete_from_question


def delete_rows(df, filters=None, question=None):
    if filters:
        matching = apply_filters(df, filters)

        if matching.empty:
            return df, (
                "No rows matched the delete filters."
            )

        removed = len(matching)

        return df.drop(
            matching.index
        ), f"Deleted {removed} row(s)."

    if question:
        return _delete_from_question(df, question)

    return df, None


def _delete_from_question(df, question):
    parsed_filters, err = build_delete_from_question(
        df,
        question,
    )

    if parsed_filters:
        return delete_rows(
            df,
            filters=parsed_filters,
        )

    if err:
        return df, err

    question_lower = question.lower().strip()

    if "missing salary" in question_lower:
        for col in df.columns:
            if "salary" in col.lower():
                cleaned = df.dropna(subset=[col])
                removed = len(df) - len(cleaned)
                return cleaned, f"Deleted {removed} row(s)."

    return df, (
        "Could not parse delete criteria. "
        "Try: remove Ayush with experience 4"
    )


delete_row = delete_rows
