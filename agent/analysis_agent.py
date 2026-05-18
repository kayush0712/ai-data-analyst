from agent.llm_client import chat
from helpers.code_helper import clean_generated_code, execute_code
from helpers.dataset_helper import build_dataset_summary


def run_analysis(question, uploaded_df):
    try:
        dataset_summary = build_dataset_summary(
            uploaded_df
        )

        prompt = f"""
You are an expert data analyst.

{dataset_summary}

User question: {question}

Write pandas code using uploaded_df (alias: df).
Rules:
- No markdown, no explanations
- No print()
- Last line must be an expression that answers the question, OR assign result = <value>
- Use only pandas operations on the dataframe
"""

        code = chat([
            {"role": "user", "content": prompt},
        ])

        code = clean_generated_code(code)

        result, error = execute_code(
            code,
            uploaded_df
        )

        if error:
            return {"error": error}

        answer = str(result).replace("\n", " ").strip()

        if len(answer) > 500:
            answer = answer[:500] + "..."

        return {"answer": answer}

    except Exception as e:
        return {"error": str(e)}
