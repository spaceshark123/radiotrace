"""Shared pytest fixtures. GridFS tests require a running MongoDB instance."""

from __future__ import annotations

import os

import pytest
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app import create_app

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
TEST_DB = "radiotrace_test"


def _mongo_available() -> bool:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    try:
        client.admin.command("ping")
        return True
    except ServerSelectionTimeoutError:
        return False
    finally:
        client.close()


@pytest.fixture(scope="session")
def mongo_uri():
    if not _mongo_available():
        pytest.skip("MongoDB is not reachable; start it with `docker compose up -d mongo`")
    return MONGO_URI


@pytest.fixture
def mongo_client(mongo_uri):
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.drop_database(TEST_DB)
    yield client
    client.drop_database(TEST_DB)
    client.close()


@pytest.fixture
def app(mongo_client):
    application = create_app(
        test_config={"MONGO_URI": MONGO_URI, "MONGO_DATABASE": TEST_DB, "TESTING": True},
        mongo_client=mongo_client,
    )
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


# A tiny constant-bitrate MP3 frame payload with enough entropy to not look blank.
VARIED_MP3 = (
    b"ID3\x04\x00\x00\x00\x00\x00\x00"
    + bytes(range(256)) * 12
)

BLANK_MP3 = b"\xff\xfb\x90\x00" + (b"\x00" * 500)
