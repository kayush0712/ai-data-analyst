import pandas as pd


ALLOWED_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def clean_generated_code(code):
    code = code.replace("```python", "")
    code = code.replace("```", "")
    code = code.strip()

    for pattern in (
        "FINAL ANSWER:",
        "OBSERVATION:",
        "ACTION:",
    ):
        if pattern in code:
            code = code.split(pattern)[0].strip()

    return code.strip()


def execute_code(code, uploaded_df):
    code = clean_generated_code(code)

    local_scope = {
        "uploaded_df": uploaded_df.copy(),
        "df": uploaded_df.copy(),
        "pd": pd,
    }

    safe_globals = {
        "__builtins__": ALLOWED_BUILTINS,
    }

    try:
        exec(
            compile(code, "<agent>", "exec"),
            safe_globals,
            local_scope
        )

        if "result" in local_scope:
            return local_scope["result"], None

        lines = [
            line
            for line in code.split("\n")
            if line.strip()
        ]

        if not lines:
            return "No result.", None

        try:
            result = eval(
                lines[-1],
                safe_globals,
                local_scope
            )
            return result, None

        except SyntaxError:
            return "Code executed successfully.", None

    except Exception as e:
        return None, str(e)
