"""MongoDB client lifecycle. All database access starts from this module."""

from __future__ import annotations

from flask import Flask, current_app, g
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
from gridfs import GridFSBucket


_client: MongoClient | None = None


def init_mongo(app: Flask, client: MongoClient | None = None) -> MongoClient:
    """Attach a Mongo client to the Flask app. Tests may inject a client."""
    global _client
    if client is not None:
        _client = client
        app.extensions["mongo_client"] = client
        return client

    uri = app.config.get("MONGO_URI", "mongodb://localhost:27017")
    _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    app.extensions["mongo_client"] = _client
    return _client


def get_client() -> MongoClient:
    if "mongo_client" in current_app.extensions:
        return current_app.extensions["mongo_client"]
    if _client is not None:
        return _client
    raise RuntimeError("MongoDB has not been initialized. Call init_mongo() first.")


def get_database() -> Database:
    name = current_app.config.get("MONGO_DATABASE", "radiotrace")
    return get_client()[name]


def get_gridfs_bucket() -> GridFSBucket:
    bucket_name = current_app.config.get("GRIDFS_BUCKET", "audio")
    return GridFSBucket(get_database(), bucket_name=bucket_name)


def ping_database() -> bool:
    try:
        get_client().admin.command("ping")
        return True
    except PyMongoError:
        return False


def close_mongo() -> None:
    global _client
    client = current_app.extensions.pop("mongo_client", None) or _client
    if client is not None:
        client.close()
    _client = None
