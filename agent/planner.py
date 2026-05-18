TASK_TYPES = [

    "analysis",

    "cleaning",

    "visualization",

    "export_csv"
]

def plan_tasks(question):

    question_lower = question.lower()

    tasks = ["analysis"]

    if any(word in question_lower for word in [
        "clean",
        "missing",
        "duplicate"
    ]):

        tasks.append(
            "cleaning"
        )

    if any(word in question_lower for word in [
        "chart",
        "graph",
        "plot",
        "visualize"
    ]):

        tasks.append(
            "visualization"
        )

    if any(word in question_lower for word in [
        "export",
        "csv",
        "download"
    ]):

        tasks.append(
            "export_csv"
        )

    return list(set(tasks))