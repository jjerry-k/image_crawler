import os
import time

import pymongo

MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB = os.getenv("MONGO_DB", "crawling")
MONGO_DATA_COLL = "data"
MONGO_DATA_TEST_COLL = "data_test"
MONGO_URI = os.getenv("MONGO_URI", f"mongodb://{MONGO_HOST}:{MONGO_PORT}")
MONGO_CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000"))
MONGO_INIT_TIMEOUT_SECONDS = int(os.getenv("MONGO_INIT_TIMEOUT_SECONDS", "60"))

MONGO_CLIENT = pymongo.MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=MONGO_CONNECT_TIMEOUT_MS,
)

JOB_KEY_INDEX = [
    ("date", pymongo.ASCENDING),
    ("key_class", pymongo.ASCENDING),
    ("keyword", pymongo.ASCENDING),
    ("class_path", pymongo.ASCENDING),
]
STATUS_INDEX = [
    ("crawled", pymongo.ASCENDING),
    ("updated_at", pymongo.DESCENDING),
]
SORT_INDEX = [
    ("date", pymongo.DESCENDING),
    ("key_class", pymongo.DESCENDING),
    ("keyword", pymongo.DESCENDING),
]


def get_collection(collection: str) -> pymongo.collection.Collection:
    return MONGO_CLIENT[MONGO_DB][collection]


def wait_for_mongo(
    timeout_seconds: int | None = None,
    poll_interval_seconds: float = 1.0,
) -> None:
    deadline = time.monotonic() + (timeout_seconds or MONGO_INIT_TIMEOUT_SECONDS)
    last_error = None

    while time.monotonic() < deadline:
        try:
            MONGO_CLIENT.admin.command("ping")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(poll_interval_seconds)

    raise RuntimeError(f"MongoDB is not ready: {last_error}")


def ensure_indexes() -> None:
    for collection_name in (MONGO_DATA_COLL, MONGO_DATA_TEST_COLL):
        coll = get_collection(collection_name)
        coll.create_index(JOB_KEY_INDEX, unique=True, name="uniq_crawl_job")
        coll.create_index(STATUS_INDEX, name="status_updated_at")
        coll.create_index(SORT_INDEX, name="date_class_keyword")


def search_doc(
    collection: str,
    filter: dict,
    projection: dict | None = None,
    sort: list[tuple[str, int]] | None = None,
    limit: int = 0,
):
    cursor = get_collection(collection).find(filter, projection)
    if sort:
        cursor = cursor.sort(sort)
    if limit:
        cursor = cursor.limit(limit)
    return cursor


def insert_doc(collection: str, document: dict):
    return get_collection(collection).insert_one(document)


def update_doc(collection: str, filter: dict, update: dict):
    return get_collection(collection).update_one(filter, update)


def find_one_doc(collection: str, filter: dict, projection: dict | None = None):
    return get_collection(collection).find_one(filter, projection)


def find_one_and_update_doc(
    collection: str,
    filter: dict,
    update: dict,
    return_document=pymongo.ReturnDocument.BEFORE,
):
    return get_collection(collection).find_one_and_update(
        filter,
        update,
        return_document=return_document,
    )


def count_docs(collection: str, filter: dict) -> int:
    return get_collection(collection).count_documents(filter)


def delete_doc(collection: str, filter: dict):
    return get_collection(collection).delete_one(filter)


def delete_docs(collection: str, filter: dict) -> int:
    result = get_collection(collection).delete_many(filter)
    return result.deleted_count
