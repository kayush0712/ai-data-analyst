from tools.cleaning_tool import clean_dataset
from tools.chart_tool import generate_chart
from tools.export_tool import export_csv
from tools.delete_tool import delete_rows
from tools.add_row_tool import add_row
from tools.update_tool import update_rows
from tools.query_tool import query_data


TOOL_DEFINITIONS = [
    {
        "name": "clean_dataset",
        "description": (
            "Remove duplicates, fill missing values, "
            "normalize column names."
        ),
        "arguments": {},
    },
    {
        "name": "generate_chart",
        "description": (
            "Create a chart. Pass x_col, y_col or "
            "mention column in question, e.g. "
            "chart of experience, salary by department."
        ),
        "arguments": {
            "x_col": "optional category column",
            "y_col": "optional numeric column",
        },
    },
    {
        "name": "export_csv",
        "description": "Export the current dataset as CSV.",
        "arguments": {},
    },
    {
        "name": "delete_rows",
        "description": (
            "Delete rows matching filters. "
            "Operators: eq, ne, contains, gt, gte, lt, lte, is_null."
        ),
        "arguments": {
            "filters": [
                {
                    "column": "string",
                    "operator": "string",
                    "value": "any",
                }
            ],
        },
    },
    {
        "name": "add_row",
        "description": "Add a new row to the dataset.",
        "arguments": {
            "row": {"column_name": "value"},
        },
    },
    {
        "name": "update_rows",
        "description": (
            "Update employee fields. Example: filters "
            "[{column: employee, operator: eq, value: Ayush}], "
            "updates {experience: 5}. Use numeric values only "
            "(5 not 5 years)."
        ),
        "arguments": {
            "filters": [
                {
                    "column": "string",
                    "operator": "string",
                    "value": "any",
                }
            ],
            "updates": {"column_name": "value"},
        },
    },
    {
        "name": "query_data",
        "description": (
            "Run pandas code for analysis. "
            "Use uploaded_df or df. "
            "Last line should be an expression, "
            "or set result = ..."
        ),
        "arguments": {
            "code": "pandas code string",
        },
    },
]


def build_tools_prompt():
    lines = ["AVAILABLE TOOLS:\n"]

    for tool in TOOL_DEFINITIONS:
        lines.append(f"- {tool['name']}: {tool['description']}")

        if tool["arguments"]:
            lines.append(
                f"  arguments: {tool['arguments']}"
            )

    return "\n".join(lines)


def execute_tool(tool_name, df, arguments=None, question=""):
    arguments = arguments or {}
    extras = {}

    if tool_name == "clean_dataset":
        return clean_dataset(df), "Dataset cleaned successfully.", extras

    if tool_name == "generate_chart":
        path = generate_chart(
            df,
            chart_type=arguments.get("chart_type", "bar"),
            x_col=arguments.get("x_col"),
            y_col=arguments.get("y_col"),
            question=question,
        )

        if not path:
            return df, (
                "Could not generate chart: "
                "column not found or not numeric."
            ), extras

        from helpers.chart_helper import (
            parse_chart_columns,
        )

        _, y_col = parse_chart_columns(df, question)
        label = y_col or "dataset"

        extras["chart_path"] = path
        extras["chart_url"] = "/" + path.replace("\\", "/")
        return df, (
            f"Chart generated for {label}."
        ), extras

    if tool_name == "export_csv":
        path = export_csv(df)
        extras["csv_export_path"] = path
        return df, "CSV exported successfully.", extras

    if tool_name == "delete_rows":
        from helpers.intent_parser import (
            build_delete_from_question,
        )

        filters = arguments.get("filters")

        if not filters:
            parsed_filters, _ = build_delete_from_question(
                df,
                question,
            )

            if parsed_filters:
                filters = parsed_filters

        if filters:
            updated, msg = delete_rows(
                df,
                filters=filters,
            )
        else:
            updated, msg = delete_rows(
                df,
                question=question,
            )

        return updated, msg or (
            "Rows deleted successfully."
        ), extras

    if tool_name == "add_row":
        from helpers.intent_parser import (
            build_add_row_from_question,
        )

        row = arguments.get("row")

        if not row:
            row, err = build_add_row_from_question(
                df,
                question,
            )

            if err:
                return df, err, extras

        if row:
            updated = add_row(df, row=row)
        else:
            updated = add_row(df, question=question)

        return updated, "Row added successfully.", extras

    if tool_name == "update_rows":
        from helpers.intent_parser import (
            build_update_from_question,
        )

        filters = arguments.get("filters")
        updates = arguments.get("updates")

        if not filters or not updates:
            parsed = build_update_from_question(
                df,
                question,
            )

            if isinstance(parsed[0], dict):
                updated, err = update_rows(
                    df,
                    filters=parsed[0],
                )

                if err:
                    return df, err, extras

                return updated, (
                    "Row updated successfully."
                ), extras

            parsed_filters, parsed_updates, parse_err = parsed

            if parsed_filters and parsed_updates:
                filters = parsed_filters
                updates = parsed_updates
            elif parse_err:
                return df, parse_err, extras

        updated, err = update_rows(
            df,
            filters=filters,
            updates=updates,
            question=question,
        )

        if err:
            updated, err = update_rows(
                df,
                question=question,
            )

            if err:
                return df, err, extras

        return updated, (
            "Row(s) updated successfully."
        ), extras

    if tool_name == "query_data":
        code = arguments.get("code", "")

        if not code:
            code = generate_analysis_code(
                question,
                df,
            )

        result = query_data(df, code)
        extras["query_result"] = str(result)
        return df, f"Query result: {result}", extras

    return df, f"Unknown tool: {tool_name}", extras


def generate_analysis_code(question, df):
    from agent.llm_client import chat
    from helpers.dataset_helper import build_dataset_summary

    prompt = f"""
{build_dataset_summary(df)}

Question: {question}

Write pandas code using uploaded_df or df.
No markdown. No print(). Last line = answer expression or result = ...
"""
    return chat([{"role": "user", "content": prompt}])


def collect_output_key(tool_name):
    mapping = {
        "clean_dataset": "cleaning",
        "generate_chart": "chart_path",
        "export_csv": "csv_export_path",
        "delete_rows": "deletion",
        "add_row": "row_addition",
        "update_rows": "row_update",
        "query_data": "query_result",
    }
    return mapping.get(tool_name)
