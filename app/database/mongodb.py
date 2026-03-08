import os
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()

# -----------------------------------
# MongoDB Configuration
# -----------------------------------

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# Global references
client: Optional[MongoClient] = None
db: Optional[Database] = None

nodes_collection: Optional[Collection] = None
doc_indexes_collection: Optional[Collection] = None
settings_collection: Optional[Collection] = None


# -----------------------------------
# Connection Functions
# -----------------------------------

def connect_mongo():
    """
    Initialize MongoDB connection and collections.
    """
    global client, db, nodes_collection, doc_indexes_collection, settings_collection

    client = MongoClient(MONGO_URI)

    db = client[DATABASE_NAME]

    nodes_collection = db["nodes"]
    doc_indexes_collection = db["doc_indexes"]
    settings_collection = db["settings"]

    # Create indexes for performance
    nodes_collection.create_index("parent_id")
    nodes_collection.create_index("type")
    nodes_collection.create_index("children_ids")

    doc_indexes_collection.create_index("document_id", unique=True)

    print("MongoDB connected")


def close_mongo():
    """
    Close MongoDB connection.
    """
    global client

    if client:
        client.close()
        print("MongoDB connection closed")


# -----------------------------------
# Helper Getters
# -----------------------------------

def get_db() -> Database:
    if db is None:
        raise Exception("Database not initialized")
    return db


def get_nodes_collection() -> Collection:
    if nodes_collection is None:
        raise Exception("Nodes collection not initialized")
    return nodes_collection


def get_doc_indexes_collection() -> Collection:
    if doc_indexes_collection is None:
        raise Exception("Doc index collection not initialized")
    return doc_indexes_collection


def get_settings_collection() -> Collection:
    if settings_collection is None:
        raise Exception("Settings collection not initialized")
    return settings_collection