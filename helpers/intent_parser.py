import re

RESERVED_NAMES = {
    "experience", "salary", "employee",
    "department", "data", "row", "rows",
    "the", "a", "an", "with", "and", "to",
    "new", "add", "insert", "chart", "csv",
    "name", "years", "year", "of",
}


def parse_experience_value(question_lower):
    patterns = [
        r"experience\s+of\s+(\d+)",
        r"with\s+experience\s+of\s+(\d+)",
        r"experience\s+of\s+[a-z]+\s+to\s+(\d+)\s*years?",
        r"experience\s+to\s+(\d+)\s*years?",
        r"to\s+(\d+)\s*years?\s+experience",
        r"(\d+)\s*years?\s+of\s+experience",
        r"(\d+)\s*years?\s+experience",
        r"experience\s+(?:of\s+[a-z]+\s+)?to\s+(\d+)",
        r"with\s+experience\s+(\d+)",
        r"set\s+experience\s+(?:to\s+)?(\d+)",
        r"change\s+experience\s+(?:to\s+)?(\d+)",
        r"update\s+experience\s+(?:to\s+)?(\d+)",
        r"add\s+(\d+)\s*years?\s+experience",
        r"experience\s+(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, question_lower)

        if match:
            return int(match.group(1))

    return None


def parse_salary_value(question_lower):
    patterns = [
        r"salary\s+of\s+(\d+)",
        r"with\s+salary\s+of\s+(\d+)",
        r"salary\s+of\s+[a-z]+\s+to\s+(\d+)",
        r"salary\s+to\s+(\d+)",
        r"set\s+salary\s+(?:to\s+)?(\d+)",
        r"change\s+salary\s+(?:to\s+)?(\d+)",
        r"update\s+salary\s+(?:to\s+)?(\d+)",
        r"salary\s+(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, question_lower)

        if match:
            return int(match.group(1))

    return None


def parse_row_index(question_lower):
    patterns = [
        r"(\d+)(?:st|nd|rd|th)\s+row",
        r"row\s+(\d+)",
        r"row\s+number\s+(\d+)",
        r"row\s+#\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, question_lower)

        if match:
            return int(match.group(1))

    return None


def parse_employee_name_for_add(question_lower):
    patterns = [
        r"employee\s+name\s+([a-zA-Z]+)",
        r"add\s+(?:a\s+)?employee\s+(?:name\s+)?([a-zA-Z]+)",
        r"employee\s+([a-zA-Z]+)",
        r"name\s+([a-zA-Z]+)\s+with",
        r"add\s+([a-zA-Z]+)\s+with",
    ]

    for pattern in patterns:
        match = re.search(pattern, question_lower)

        if match:
            candidate = match.group(1).title()

            if candidate.lower() not in RESERVED_NAMES:
                return candidate

    return None


def find_employee_name(df, question_lower):
    employee_col = None

    for col in df.columns:
        if col.lower() in ("employee", "name"):
            employee_col = col
            break

    if not employee_col:
        return None, None

    parsed_name = parse_employee_name_for_add(
        question_lower
    )

    if parsed_name:
        return employee_col, parsed_name

    for value in df[employee_col].dropna().astype(str):
        name = value.strip()

        if not name or name.lower() == "nan":
            continue

        if name.lower() in question_lower:
            return employee_col, name

    name_patterns = [
        r"experience\s+of\s+([a-zA-Z]+)",
        r"salary\s+of\s+([a-zA-Z]+)",
        r"update\s+([a-zA-Z]+)(?:'s|\s)",
        r"change\s+([a-zA-Z]+)(?:'s|\s)",
        r"modify\s+([a-zA-Z]+)(?:'s|\s)",
        r"for\s+([a-zA-Z]+)\s+",
    ]

    for pattern in name_patterns:
        match = re.search(pattern, question_lower)

        if match:
            candidate = match.group(1).title()

            if candidate.lower() not in RESERVED_NAMES:
                return employee_col, candidate

    return employee_col, None


def validate_employee_name(name):
    if not name:
        return (
            False,
            "Employee name is required.",
        )

    if str(name).lower() in RESERVED_NAMES:
        return (
            False,
            (
                f"'{name}' is not a valid employee name. "
                "Use a person's name like Ayush."
            ),
        )

    return True, None


def validate_add_request(question):
    question_lower = question.lower().strip()

    if re.search(
        r"^\s*add\s+(experience|salary)\b",
        question_lower,
    ):
        return (
            False,
            (
                "Experience and salary must be numeric "
                "values. Try: Add employee Ayush with "
                "experience 3 and salary 80000."
            ),
        )

    if re.search(
        r"\badd\s+(experience|salary)\s+of\b",
        question_lower,
    ) and "employee" not in question_lower:
        return (
            False,
            (
                "That looks like an update, not a new row. "
                "Try: Update experience of Ayush to 5."
            ),
        )

    return True, None


def coerce_numeric(value):
    if isinstance(value, (int, float)):
        return value

    match = re.search(
        r"(\d+\.?\d*)",
        str(value)
    )

    if match:
        number = float(match.group(1))

        if number.is_integer():
            return int(number)

        return number

    return value


def _build_field_updates(df, question_lower):
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

    for dept in (
        "finance", "marketing",
        "engineering", "hr", "sales",
    ):
        if dept in question_lower:
            for col in df.columns:
                if "department" in col.lower():
                    updates[col] = dept.title()

    return updates


def build_update_from_question(df, question):
    question_lower = question.lower().strip()

    updates = _build_field_updates(
        df,
        question_lower,
    )

    if not updates:
        return None, None, "Could not parse fields to update."

    row_num = parse_row_index(question_lower)

    if row_num is not None:
        index_pos = row_num - 1

        if index_pos < 0 or index_pos >= len(df):
            return None, None, (
                f"Row {row_num} does not exist. "
                f"Dataset has {len(df)} rows."
            )

        target_index = df.index[index_pos]

        return {
            "row_index": target_index,
            "updates": updates,
        }, None, None

    employee_col, employee_name = find_employee_name(
        df,
        question_lower,
    )

    if not employee_col or not employee_name:
        return None, None, (
            "Employee not found in question. "
            "Use a name or row number, e.g. "
            "'update 10th row experience to 7'."
        )

    valid, err = validate_employee_name(employee_name)

    if not valid:
        return None, None, err

    filters = [
        {
            "column": employee_col,
            "operator": "eq",
            "value": employee_name,
        }
    ]

    return filters, updates, None


def build_delete_from_question(df, question):
    question_lower = question.lower().strip()

    delete_words = (
        "delete", "remove", "drop", "eliminate",
    )

    if not any(
        word in question_lower
        for word in delete_words
    ):
        return None, "Not a delete request."

    filters = []

    employee_col, employee_name = find_employee_name(
        df,
        question_lower,
    )

    if employee_name and employee_col:
        filters.append({
            "column": employee_col,
            "operator": "eq",
            "value": employee_name,
        })

    experience = parse_experience_value(question_lower)

    if experience is None:
        exp_match = re.search(
            r"(?:with|having)\s+experience\s+(\d+)",
            question_lower,
        )

        if exp_match:
            experience = int(exp_match.group(1))

    if experience is not None:
        for col in df.columns:
            if "experience" in col.lower():
                filters.append({
                    "column": col,
                    "operator": "eq",
                    "value": experience,
                })

    salary = parse_salary_value(question_lower)

    if salary is not None:
        for col in df.columns:
            if "salary" in col.lower():
                filters.append({
                    "column": col,
                    "operator": "eq",
                    "value": salary,
                })

    for dept in (
        "finance", "marketing",
        "engineering", "hr", "sales",
    ):
        if dept in question_lower:
            for col in df.columns:
                if "department" in col.lower():
                    filters.append({
                        "column": col,
                        "operator": "eq",
                        "value": dept.title(),
                    })

    if not filters:
        return None, (
            "Could not parse delete criteria. "
            "Try: remove Ayush with experience 4"
        )

    return filters, None


def build_add_row_from_question(df, question):
    question_lower = question.lower().strip()

    if not any(
        word in question_lower
        for word in (
            "add", "insert", "append", "create",
        )
    ):
        return None, None

    valid, err = validate_add_request(question)

    if not valid:
        return None, err

    employee_name = parse_employee_name_for_add(
        question_lower
    )

    if not employee_name:
        return None, (
            "Could not find employee name. "
            "Use: Add employee Ayush with "
            "experience 3 and salary 80000"
        )

    name_ok, name_err = validate_employee_name(
        employee_name
    )

    if not name_ok:
        return None, name_err

    row = {}

    for col in df.columns:
        if col.lower() in ("employee", "name"):
            row[col] = employee_name

    row.update(
        _build_field_updates(df, question_lower)
    )

    if len(row) <= 1:
        return None, (
            "Could not parse row fields. "
            "Include experience or salary as numbers."
        )

    return row, None
