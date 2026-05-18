import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

_collection = None


def get_datasets_collection():
    global _collection

    if not MONGO_URI:
        return None

    if _collection is None:
        client = MongoClient(MONGO_URI)
        db = client["ai_data_analyst"]
        _collection = db["datasets"]

    return _collection


def get_chat_collection():
    if not MONGO_URI:
        return None

    client = MongoClient(MONGO_URI)
    return client["ai_data_analyst"]["chat_history"]


class _LazyCollection:
    def __bool__(self):
        return get_datasets_collection() is not None

    def __getattr__(self, item):
        collection = get_datasets_collection()

        if collection is None:
            raise RuntimeError(
                "MONGO_URI is not configured."
            )

        return getattr(collection, item)


datasets_collection = _LazyCollection()
chat_collection = None
