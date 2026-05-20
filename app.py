import os

import cloudinary.uploader
import pandas as pd
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

from config import MPLCONFIGDIR, MONGO_URI
from database.mongo import get_datasets_collection
from routes.analyze_routes import analyze_bp
from services.cloudinary_storage import configure_cloudinary
from services import dataset_service

os.makedirs(MPLCONFIGDIR, exist_ok=True)
os.environ["MPLCONFIGDIR"] = MPLCONFIGDIR

os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_charts", exist_ok=True)
os.makedirs("generated_csv", exist_ok=True)

app = Flask(__name__)
app.register_blueprint(analyze_bp)

configure_cloudinary()


def _require_database():
    if not MONGO_URI:
        raise RuntimeError(
            "MONGO_URI is not configured."
        )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        _require_database()

        if "file" not in request.files:
            return jsonify({
                "error": "No file uploaded",
            }), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({
                "error": "Empty filename",
            }), 400

        upload_result = cloudinary.uploader.upload(
            file,
            resource_type="raw",
            folder="ai_data_analyst/datasets",
        )

        file_url = upload_result["secure_url"]
        df = pd.read_csv(file_url)

        dataset_id = dataset_service.register_dataset(
            df,
            file.filename,
            file_url=file_url,
        )

        datasets, _ = dataset_service.list_datasets()

        meta = dataset_service.get_dataset(dataset_id)

        return jsonify({
            "message": "CSV uploaded successfully",
            "dataset_id": dataset_id,
            "filename": file.filename,
            "rows": meta["rows"],
            "columns": meta["columns"],
            "datasets": datasets,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/datasets", methods=["GET"])
def get_datasets():
    try:
        _require_database()

        datasets, active_id = dataset_service.list_datasets()

        return jsonify({
            "datasets": datasets,
            "active_dataset_id": active_id,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/datasets/active", methods=["POST"])
def set_active_dataset_route():
    try:
        _require_database()

        body = request.get_json() or {}
        dataset_id = body.get("dataset_id")

        if not dataset_id:
            return jsonify({
                "error": "dataset_id required",
            }), 400

        doc = dataset_service.set_active_dataset(
            dataset_id,
        )

        if not doc:
            return jsonify({
                "error": "Dataset not found",
            }), 404

        datasets, _ = dataset_service.list_datasets()

        return jsonify({
            "message": (
                f"Switched to {doc['filename']}"
            ),
            "dataset_id": dataset_id,
            "filename": doc["filename"],
            "rows": doc.get("rows", 0),
            "datasets": datasets,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generated_charts/<path:filename>")
def serve_chart(filename):
    return send_from_directory(
        "generated_charts",
        filename,
    )


@app.route("/generated_csv/<path:filename>")
def serve_csv(filename):
    return send_from_directory(
        "generated_csv",
        filename,
        as_attachment=True,
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=8000)