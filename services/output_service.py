import os

from services.cloudinary_storage import upload_local_file


def publish_outputs(outputs):
    published = dict(outputs)

    chart_path = published.get("chart_path")

    if chart_path and os.path.exists(chart_path):
        published["chart_url"] = upload_local_file(
            chart_path,
            folder="ai_data_analyst/charts",
        )

    csv_path = published.get("csv_export_path")

    if csv_path and os.path.exists(csv_path):
        published["csv_export_url"] = upload_local_file(
            csv_path,
            folder="ai_data_analyst/exports",
        )

    return published
