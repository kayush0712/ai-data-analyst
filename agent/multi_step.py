import re

from agent.tool_registry import execute_tool
from helpers.dtype_helper import prepare_dataframe

CHART_WORDS = (
    "chart", "graph", "plot", "visualize",
    "visualise", "visualization", "visualisation",
)

ANALYSIS_WORDS = (
    "average", "mean", "median", "sum", "count",
    "highest", "lowest", "maximum", "minimum",
    "who", "which", "compare", "total", "how many",
    "what is", "what's",
)


def detect_tool_sequence(question):
    q = question.lower()
    sequence = []

    if re.search(
        r"\b(clean|missing|duplicate|duplicates)\b",
        q,
    ):
        sequence.append("clean_dataset")

    needs_analysis = any(
        word in q for word in ANALYSIS_WORDS
    )

    needs_chart = any(
        word in q for word in CHART_WORDS
    )

    needs_export = bool(
        re.search(
            r"\b(export|download|save)\b",
            q,
        )
        and re.search(r"\b(csv|file|data)\b", q)
        or "export csv" in q
        or "download csv" in q
    )

    if needs_analysis:
        sequence.append("query_data")

    if needs_chart:
        sequence.append("generate_chart")

    if needs_export:
        sequence.append("export_csv")

    return sequence


def is_multi_step_question(question):
    sequence = detect_tool_sequence(question)

    if len(sequence) >= 2:
        return True

    if re.search(r"\bthen\b", question, re.I):
        return len(sequence) >= 1

    if question.count(",") >= 2 and sequence:
        return True

    return False


def _analysis_subquestion(question):
    parts = re.split(
        r"\bthen\b|\band then\b",
        question,
        flags=re.I,
    )

    first = parts[0].strip()

    for sep in (",", " and "):
        if sep in first.lower():
            chunks = re.split(
                r",|\band\b",
                first,
                flags=re.I,
            )

            for chunk in chunks:
                chunk_lower = chunk.lower()

                if any(
                    word in chunk_lower
                    for word in ANALYSIS_WORDS
                ):
                    return chunk.strip()

    return first


def run_multi_step(question, df):
    sequence = detect_tool_sequence(question)

    if not sequence:
        return None

    if len(sequence) < 2 and not re.search(
        r"\bthen\b",
        question,
        re.I,
    ):
        return None

    current_df = prepare_dataframe(df)
    outputs = {}
    observations = []

    for tool_name in sequence:
        tool_question = question

        if tool_name == "query_data":
            tool_question = _analysis_subquestion(
                question
            )

        current_df, observation, extras = execute_tool(
            tool_name,
            current_df,
            question=tool_question,
        )

        outputs.update(extras)
        observations.append(observation)

    answer_parts = []

    for item in observations:
        if item.startswith("Query result:"):
            answer_parts.append(
                item.replace("Query result:", "").strip()
            )
        elif "successfully" in item.lower():
            answer_parts.append(item)

    answer = " ".join(answer_parts).strip()

    if not answer:
        answer = "Completed all requested steps."

    return {
        "answer": answer,
        "outputs": outputs,
        "dataframe": current_df,
    }
