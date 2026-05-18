import pandas as pd


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


def add_row(df, row=None, question=None):
    new_row = {col: None for col in df.columns}

    if row:
        for key, value in row.items():
            col = _resolve_column(df, key)

            if col is not None:
                new_row[col] = value

    elif question:
        new_row = _row_from_question(
            df,
            new_row,
            question
        )

    return pd.concat(
        [df, pd.DataFrame([new_row])],
        ignore_index=True
    )


def _row_from_question(df, new_row, question):
    import re

    question_lower = question.lower().strip()

    match = re.search(
        r'row of ([a-zA-Z]+)|add ([a-zA-Z]+)',
        question_lower
    )

    if match:
        name = (match.group(1) or match.group(2)).title()

        for col in df.columns:
            if col.lower() in ("employee", "name"):
                new_row[col] = name

    exp_match = re.search(
        r'experience(?: of)?(?: to)?\s*(\d+)',
        question_lower
    )

    if exp_match:
        for col in df.columns:
            if "experience" in col.lower():
                new_row[col] = int(exp_match.group(1))

    salary_match = re.search(
        r'salary(?: of)?(?: to)?\s*(\d+)',
        question_lower
    )

    if salary_match:
        for col in df.columns:
            if "salary" in col.lower():
                new_row[col] = int(salary_match.group(1))

    for dept in (
        "finance", "marketing",
        "engineering", "hr", "sales"
    ):
        if dept in question_lower:
            for col in df.columns:
                if "department" in col.lower():
                    new_row[col] = dept.title()

    return new_row
