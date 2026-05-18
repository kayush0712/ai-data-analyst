import io
import os
import uuid

import cloudinary
import cloudinary.uploader
import pandas as pd

from config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_URL,
)


def configure_cloudinary():
    if CLOUDINARY_URL:
        cloudinary.config(secure=True)
        return

    if (
        CLOUDINARY_CLOUD_NAME
        and CLOUDINARY_API_KEY
        and CLOUDINARY_API_SECRET
    ):
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True,
        )


def upload_dataframe_csv(df, label="dataset"):
    configure_cloudinary()

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    public_id = (
        f"ai_data_analyst/datasets/"
        f"{label}_{uuid.uuid4().hex}"
    )

    result = cloudinary.uploader.upload(
        buffer.getvalue().encode("utf-8"),
        resource_type="raw",
        public_id=public_id,
    )

    return result["secure_url"]


def upload_local_file(local_path, folder="ai_data_analyst"):
    configure_cloudinary()

    resource_type = "image"

    if local_path.endswith(".csv"):
        resource_type = "raw"

    result = cloudinary.uploader.upload(
        local_path,
        resource_type=resource_type,
        folder=folder,
    )

    return result["secure_url"]


def load_dataframe_from_url(file_url):
    return pd.read_csv(file_url)
