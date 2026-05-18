from flask import Blueprint, request, jsonify
import pandas as pd
import cloudinary.uploader

from database.mongo import datasets_collection

from datetime import datetime, UTC

upload_bp = Blueprint(
    "upload_bp",
    __name__
)

@upload_bp.route(
    "/upload",
    methods=["POST"]
)
def upload_file():

    try:

        if "file" not in request.files:

            return jsonify({
                "error": "No file uploaded"
            }), 400

        file = request.files["file"]

        upload_result = cloudinary.uploader.upload(
            file,
            resource_type="raw",
            folder="ai_data_analyst"
        )

        file_url = upload_result[
            "secure_url"
        ]

        uploaded_df = pd.read_csv(file_url)

        dataset_data = {
            "filename": file.filename,
            "file_url": file_url,
            "columns": uploaded_df.columns.tolist(),
            "rows": len(uploaded_df),
            "uploaded_at": datetime.now(UTC)
        }

        existing = datasets_collection.find_one({
            "filename": file.filename
        })

        if existing:

            datasets_collection.update_one(
                {
                    "filename": file.filename
                },
                {
                    "$set": dataset_data
                }
            )

        else:

            datasets_collection.insert_one(
                dataset_data
            )

        return jsonify({
            "message": "CSV uploaded successfully",
            "filename": file.filename,
            "rows": len(uploaded_df),
            "columns": uploaded_df.columns.tolist()
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500