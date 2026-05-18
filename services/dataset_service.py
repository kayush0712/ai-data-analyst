import uuid
from datetime import datetime, UTC

from helpers.dtype_helper import prepare_dataframe
from database.mongo import datasets_collection
from services.cloudinary_storage import (
    load_dataframe_from_url,
    upload_dataframe_csv,
)


def register_dataset(df, filename, file_url=None):
    dataset_id = str(uuid.uuid4())
    prepared = prepare_dataframe(df)

    if not file_url:
        file_url = upload_dataframe_csv(
            prepared,
            label=filename.replace(".csv", ""),
        )

    doc = {
        "dataset_id": dataset_id,
        "filename": filename,
        "file_url": file_url,
        "columns": prepared.columns.tolist(),
        "rows": len(prepared),
        "uploaded_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "is_active": True,
    }

    datasets_collection.update_many(
        {},
        {"$set": {"is_active": False}},
    )

    datasets_collection.insert_one(doc)

    return dataset_id


def list_datasets():
    items = []
    active_id = None

    for doc in datasets_collection.find().sort(
        "uploaded_at",
        -1,
    ):
        dataset_id = doc.get("dataset_id")

        if doc.get("is_active"):
            active_id = dataset_id

        items.append({
            "id": dataset_id,
            "filename": doc.get("filename", ""),
            "rows": doc.get("rows", 0),
            "columns": doc.get("columns", []),
            "is_active": bool(doc.get("is_active")),
        })

    return items, active_id


def set_active_dataset(dataset_id):
    doc = datasets_collection.find_one({
        "dataset_id": dataset_id,
    })

    if not doc:
        return None

    datasets_collection.update_many(
        {},
        {"$set": {"is_active": False}},
    )

    datasets_collection.update_one(
        {"dataset_id": dataset_id},
        {"$set": {"is_active": True}},
    )

    return doc


def get_dataset(dataset_id=None):
    query = {}

    if dataset_id:
        query["dataset_id"] = dataset_id
    else:
        query["is_active"] = True

    doc = datasets_collection.find_one(
        query,
        sort=[("uploaded_at", -1)],
    )

    if not doc:
        return None

    df = load_dataframe_from_url(
        doc["file_url"],
    )
    prepared = prepare_dataframe(df)

    return {
        "dataset_id": doc["dataset_id"],
        "filename": doc["filename"],
        "file_url": doc["file_url"],
        "columns": doc.get("columns", []),
        "rows": len(prepared),
        "dataframe": prepared,
    }


def update_dataset_dataframe(dataset_id, df):
    prepared = prepare_dataframe(df)
    file_url = upload_dataframe_csv(
        prepared,
        label=f"updated_{dataset_id[:8]}",
    )

    datasets_collection.update_one(
        {"dataset_id": dataset_id},
        {
            "$set": {
                "file_url": file_url,
                "rows": len(prepared),
                "columns": prepared.columns.tolist(),
                "updated_at": datetime.now(UTC),
            }
        },
    )

    return file_url
