from flask import Blueprint, jsonify

from database.mongo import datasets_collection

dataset_bp = Blueprint(
    "dataset_bp",
    __name__
)

@dataset_bp.route(
    "/datasets",
    methods=["GET"]
)
def get_datasets():

    try:

        datasets = []

        for dataset in datasets_collection.find().sort(
            "uploaded_at",
            -1
        ):

            datasets.append({
                "filename": dataset["filename"],
                "rows": dataset["rows"],
                "columns": dataset["columns"]
            })

        return jsonify({
            "datasets": datasets,
            "total": len(datasets)
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500