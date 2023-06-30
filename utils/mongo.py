MONGO_HOST = "mongo"
MONGO_PORT = "27017"
MONGO_DB = "crawling"
MONGO_DATA_COLL = "data"
MONGO_DATA_TEST_COLL = "data_test"

import pymongo

MONGO_CLIENT = pymongo.MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}")

def search_doc(collection: str, filter: dict) -> pymongo.collection.Collection:
    """Search document using filter 

    Args:
        collection (str): Mongo db collection
        filter (dict): Query filter

    Returns:
        pymongo.collection.Collection: DB list generator
    """
    coll = MONGO_CLIENT[MONGO_DB][collection]
    return coll.find(filter)

def insert_doc(collection: str, document: dict) -> None:
    """Insert document

    Args:
        collection (str): Mongo db collection
        document (dict): Query filter
    """
    MONGO_CLIENT[MONGO_DB][collection].insert_one(document)


def update_doc(collection: str, filter: dict, update: dict) -> None:
    """Update doc using filter

    Args:
        collection (str): Mongo db collection
        filter (dict): Query filter
        update (dict): Update filter
    """
    # ex MONGO_CLIENT[MONGO_DB][collection].update_one({"name":"sangrae", "age": 29}, {"$set": {"age": 30}})
    MONGO_CLIENT[MONGO_DB][collection].update_one(filter, update)
    pass

def delete_doc(collection: str, filter: dict) -> None:
    """Delete doc using filter

    Args:
        collection (str): Mongo db collection
        filter (dict): Update filter
    """
    # MONGO_CLIENT[MONGO_DB][collection].delete_one({"name": "sangrae"})
    MONGO_CLIENT[MONGO_DB][collection].delete_one(filter)
    pass