from tools.filters import apply_filters
from helpers.intent_parser import (
    build_update_from_question,
    coerce_numeric,
    find_employee_name,
    parse_experience_value,
    parse_row_index,
    parse_salary_value,
)


def _resolve_column(df, key):
    if key in df.columns:
        return key

    key_lower = key.lower().strip()

    for col in df.columns:
        if col.lower() == key_lower:
            return col

    for col in df.columns:
        if key_lower in col.lower():
            return col

    return None


def _normalize_updates(df, updates):
    normalized = {}

    for key, value in updates.items():
        col = _resolve_column(df, key)

        if col is None:
            continue

        if "experience" in col.lower() or "salary" in col.lower():
            normalized[col] = coerce_numeric(value)
        else:
            normalized[col] = value

    return normalized


def _apply_updates_to_index(df, target_index, updates):
    result = df.copy()
    updates = _normalize_updates(result, updates)

    for col, value in updates.items():
        result.loc[target_index, col] = value

    return result, None


def update_rows(df, filters=None, updates=None, question=None):
    result = df.copy()

    if isinstance(filters, dict) and "row_index" in filters:
        return _apply_updates_to_index(
            result,
            filters["row_index"],
            filters.get("updates", updates or {}),
        )

    if filters and updates:
        updates = _normalize_updates(result, updates)
        matching = apply_filters(result, filters)

        if matching.empty and question:
            parsed = build_update_from_question(
                result,
                question,
            )

            if isinstance(parsed[0], dict):
                return _apply_updates_to_index(
                    result,
                    parsed[0]["row_index"],
                    parsed[0]["updates"],
                )

            parsed_filters, parsed_updates, err = parsed

            if err:
                return result, err

            if parsed_filters and parsed_updates:
                filters = parsed_filters
                updates = parsed_updates
                matching = apply_filters(
                    result,
                    filters,
                )

        if matching.empty:
            name = filters[0].get("value") if filters else None

            return result, (
                f"No rows found"
                + (f" for: {name}" if name else ".")
            )

        for col, value in updates.items():
            result.loc[matching.index, col] = value

        return result, None

    if question:
        return _update_from_question(result, question)

    return result, None


def _update_from_question(df, question):
    question_lower = question.lower().strip()

    updates = {}

    experience = parse_experience_value(question_lower)

    if experience is not None:
        for col in df.columns:
            if "experience" in col.lower():
                updates[col] = experience

    salary = parse_salary_value(question_lower)

    if salary is not None:
        for col in df.columns:
            if "salary" in col.lower():
                updates[col] = salary

    if not updates:
        return df, "Could not parse what to update."

    row_num = parse_row_index(question_lower)

    if row_num is not None:
        index_pos = row_num - 1

        if index_pos < 0 or index_pos >= len(df):
            return df, (
                f"Row {row_num} does not exist. "
                f"Dataset has {len(df)} rows."
            )

        return _apply_updates_to_index(
            df,
            df.index[index_pos],
            updates,
        )

    employee_col, employee_name = find_employee_name(
        df,
        question_lower,
    )

    if not employee_col or not employee_name:
        return df, (
            "Employee not found in question. "
            "Use a name or row number."
        )

    mask = (
        df[employee_col].astype(str).str.lower()
        == employee_name.lower()
    )

    if not mask.any():
        return df, (
            f"No employee named {employee_name} "
            "in the dataset."
        )

    result = df.copy()

    for col, value in updates.items():
        resolved = _resolve_column(result, col)

        if resolved:
            result.loc[mask, resolved] = value

    return result, None


update_row = update_rows
