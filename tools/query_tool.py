from helpers.code_helper import execute_code


def query_data(df, code):
    if not code or not str(code).strip():
        return "No code provided."

    result, error = execute_code(
        str(code).strip(),
        df
    )

    if error:
        return f"Error: {error}"

    return str(result)
