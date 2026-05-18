from tools.cleaning_tool import clean_dataset
from tools.chart_tool import generate_chart
from tools.export_tool import export_csv

def execute_agent_tasks(tasks, uploaded_df):

    outputs = {}

    current_df = uploaded_df.copy()

    # CLEANING
    if "cleaning" in tasks:

        current_df = clean_dataset(
            current_df
        )

        outputs[
            "cleaning"
        ] = "Dataset cleaned successfully"

    # VISUALIZATION
    if "visualization" in tasks:

        chart_path = generate_chart(
            current_df
        )

        outputs[
            "chart_path"
        ] = chart_path

    # EXPORT CSV
    if "export_csv" in tasks:

        csv_path = export_csv(
            current_df
        )

        outputs[
            "csv_export_path"
        ] = csv_path

    return current_df, outputs