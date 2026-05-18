from flask import Blueprint, jsonify, request

from config import TABLE_DISPLAY_LIMIT, MONGO_URI
from agent.tool_agent import run_agent
from helpers.json_helper import dataframe_to_records
from services import dataset_service
from services.output_service import publish_outputs

analyze_bp = Blueprint(
    "analyze_bp",
    __name__,
)


@analyze_bp.route("/analyze", methods=["POST"])
def analyze():
    try:
        if not MONGO_URI:
            return jsonify({
                "error": (
                    "Database not configured. "
                    "Set MONGO_URI on the server."
                ),
            }), 500

        body = request.get_json()

        if not body:
            return jsonify({
                "error": "Missing request body",
            }), 400

        question = body.get("question", "").strip()

        if not question:
            return jsonify({
                "error": "Question required",
            }), 400

        dataset_id = body.get("dataset_id")

        meta = dataset_service.get_dataset(dataset_id)

        if not meta:
            return jsonify({
                "error": (
                    "Upload a CSV first, or select "
                    "a dataset from the sidebar."
                ),
            }), 400

        if dataset_id:
            dataset_service.set_active_dataset(
                dataset_id,
            )

        uploaded_df = meta["dataframe"].copy()
        active_id = meta["dataset_id"]

        result = run_agent(
            question,
            uploaded_df,
        )

        cleaned_df = result.get(
            "dataframe",
            uploaded_df,
        )

        dataset_service.update_dataset_dataframe(
            active_id,
            cleaned_df,
        )

        total_rows = len(cleaned_df)
        limit = TABLE_DISPLAY_LIMIT
        displayed = min(total_rows, limit)

        table_data = dataframe_to_records(
            cleaned_df,
            limit=limit,
        )

        answer = result.get("answer", "")

        if result.get("error") and not answer:
            answer = result["error"]

        outputs = publish_outputs(
            result.get("outputs", {}),
        )

        chart_url = outputs.get("chart_url")

        csv_url = (
            outputs.get("csv_export_url")
            or outputs.get("csv_export_path")
        )

        if csv_url and not csv_url.startswith("http"):
            csv_url = "/" + csv_url.lstrip("/")

        active_meta = dataset_service.get_dataset(
            active_id,
        )

        return jsonify({
            "answer": answer,
            "outputs": outputs,
            "chart_url": chart_url,
            "csv_url": csv_url,
            "table": table_data,
            "total_rows": total_rows,
            "displayed_rows": displayed,
            "dataset_id": active_id,
            "dataset_name": active_meta["filename"],
            "warning": result.get("error"),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
