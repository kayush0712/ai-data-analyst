import json
import os
import re

from agent.llm_client import chat
from agent.multi_step import (
    is_multi_step_question,
    run_multi_step,
)
from agent.tool_registry import (
    build_tools_prompt,
    collect_output_key,
    execute_tool,
    TOOL_DEFINITIONS,
)
from helpers.dataset_helper import build_dataset_summary
from helpers.dtype_helper import prepare_dataframe
from helpers.intent_parser import (
    build_add_row_from_question,
    build_delete_from_question,
    parse_experience_value,
    parse_row_index,
    parse_salary_value,
)
from tools.update_tool import update_rows
from tools.chart_tool import generate_chart
from tools.delete_tool import delete_rows
from tools.add_row_tool import add_row
from tools.cleaning_tool import clean_dataset


VALID_TOOLS = {t["name"] for t in TOOL_DEFINITIONS}

UPDATE_WORDS = (
    "update", "change", "modify", "set", "edit",
)

DELETE_WORDS = (
    "delete", "remove", "drop", "eliminate",
)

ADD_WORDS = (
    "add", "insert", "append", "create",
)

CHART_WORDS = (
    "chart", "graph", "plot", "visualize",
    "visualise", "visualization", "visualisation",
    "diagram", "show",
)

SYSTEM_PROMPT = """
You are an autonomous AI data analyst agent.

{tools_prompt}

DATASET CONTEXT:
{dataset_summary}

RESPONSE FORMAT — valid JSON only, no markdown:

Tool call:
{{
  "action": "tool",
  "tool": "<tool_name>",
  "arguments": {{ }}
}}

Final answer:
{{
  "action": "final",
  "answer": "<short user-facing answer>"
}}

RULES:
1. Call only ONE tool per step.
2. For analysis, use query_data with pandas on uploaded_df or df.
3. For employee edits, use update_rows — NOT query_data.
4. For charts, use generate_chart — NOT query_data.
5. For delete, pass ALL filters (name + experience + salary if given).
6. Never include file paths in the final answer.
7. Keep final answers under 2 sentences.
"""


def _is_valid_chart_path(path) -> bool:
    """
    Return True only if path is a real generated chart file path.
    Rejects None, empty strings, error messages, or anything that
    doesn't look like a generated_charts/*.png path.
    """
    if not path or not isinstance(path, str):
        return False
    # Must start with the charts directory and end with .png
    normalized = path.replace("\\", "/")
    return normalized.startswith("generated_charts/") and normalized.endswith(".png")


def try_direct_clean(question, df):
    question_lower = question.lower()

    if not re.search(
        r"\b(clean|missing|duplicate)\b",
        question_lower,
    ):
        return None

    if is_multi_step_question(question):
        return None

    cleaned = clean_dataset(df)

    return {
        "answer": (
            "Dataset cleaned: duplicates removed, "
            "missing values filled."
        ),
        "outputs": {"cleaning": "success"},
        "dataframe": cleaned,
    }


def try_direct_chart(question, df):
    if is_multi_step_question(question):
        return None

    question_lower = question.lower()

    if not any(word in question_lower for word in CHART_WORDS):
        return None

    if any(word in question_lower for word in UPDATE_WORDS) and (
        parse_experience_value(question_lower)
        or parse_salary_value(question_lower)
    ):
        return None

    from helpers.chart_helper import parse_chart_columns

    prepared = prepare_dataframe(df)

    path = generate_chart(prepared, question=question)

    # Strictly validate the returned path — generate_chart (or tool_registry)
    # may return an error string instead of None on failure; catch both cases.
    if not _is_valid_chart_path(path):
        return {
            "answer": (
                "Could not create a chart. "
                "Please check the column name exists "
                "and has numeric values."
            ),
            "outputs": {},
            "dataframe": prepared,
        }

    _, y_col = parse_chart_columns(prepared, question)
    column_label = y_col or "your data"
    chart_url = "/" + path.replace("\\", "/")

    return {
        "answer": f"Here is a chart of {column_label}.",
        "outputs": {
            "chart_path": path,
            "chart_url": chart_url,
        },
        "dataframe": prepared,
    }


def try_direct_update(question, df):
    question_lower = question.lower()

    if not any(word in question_lower for word in UPDATE_WORDS):
        return None

    if not (
        parse_experience_value(question_lower)
        or parse_salary_value(question_lower)
        or parse_row_index(question_lower)
    ):
        return None

    updated, err = update_rows(df, question=question)

    if err:
        return {
            "answer": err,
            "outputs": {},
            "dataframe": df,
        }

    return {
        "answer": "Employee record updated successfully.",
        "outputs": {"row_update": "success"},
        "dataframe": updated,
    }


def try_direct_delete(question, df):
    question_lower = question.lower()

    if not any(word in question_lower for word in DELETE_WORDS):
        return None

    filters, err = build_delete_from_question(df, question)

    if not filters:
        return None

    updated, msg = delete_rows(df, filters=filters)

    return {
        "answer": msg or "Rows deleted successfully.",
        "outputs": {"deletion": msg},
        "dataframe": updated,
    }


def try_direct_add(question, df):
    question_lower = question.lower()

    if not any(word in question_lower for word in ADD_WORDS):
        return None

    if any(word in question_lower for word in CHART_WORDS + DELETE_WORDS):
        return None

    row, err = build_add_row_from_question(df, question)

    if err:
        return {
            "answer": err,
            "outputs": {},
            "dataframe": df,
        }

    if not row:
        return None

    updated = add_row(df, row=row)

    return {
        "answer": "Row added successfully.",
        "outputs": {"row_addition": "success"},
        "dataframe": updated,
    }


def extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group())
        except Exception:
            return None

    return None


def run_agent(question, uploaded_df):
    current_df = prepare_dataframe(uploaded_df.copy())
    outputs = {}

    multi = run_multi_step(question, current_df)

    if multi is not None:
        return multi

    for handler in (
        try_direct_delete,
        try_direct_add,
        try_direct_update,
        try_direct_clean,
        try_direct_chart,
    ):
        direct = handler(question, current_df)

        if direct is not None:
            return direct

    dataset_summary = build_dataset_summary(current_df)

    system_content = SYSTEM_PROMPT.format(
        tools_prompt=build_tools_prompt(),
        dataset_summary=dataset_summary,
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]

    for step in range(12):
        ai_message = chat(messages)

        if not ai_message:
            messages.append({
                "role": "user",
                "content": "Respond with valid JSON only.",
            })
            continue

        parsed = extract_json(ai_message)

        if not parsed:
            messages.append({
                "role": "user",
                "content": "Invalid JSON. Return valid JSON only.",
            })
            continue

        action = parsed.get("action")

        if action == "final":
            return {
                "answer": parsed.get("answer", "Task completed."),
                "outputs": outputs,
                "dataframe": current_df,
            }

        if action != "tool":
            messages.append({
                "role": "user",
                "content": 'Use action "tool" or "final".',
            })
            continue

        tool_name = parsed.get("tool")
        arguments = parsed.get("arguments") or {}

        if tool_name not in VALID_TOOLS:
            observation = f"Invalid tool: {tool_name}"
        else:
            current_df, observation, extras = execute_tool(
                tool_name,
                current_df,
                arguments=arguments,
                question=question,
            )

            outputs.update(extras)

            output_key = collect_output_key(tool_name)

            if output_key and output_key not in extras:
                outputs[output_key] = observation

        messages.append({
            "role": "assistant",
            "content": ai_message,
        })
        messages.append({
            "role": "user",
            "content": f"OBSERVATION: {observation}",
        })

    return {
        "error": "Agent reached max steps",
        "outputs": outputs,
        "dataframe": current_df,
    }