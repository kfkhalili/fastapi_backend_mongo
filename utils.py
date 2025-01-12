# utils.py

import logging
import tomllib
import pandas as pd

from pathlib import Path
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
 

logger = logging.getLogger(__name__)

def get_mongo_client(mongo_uri: str) -> MongoClient:
    """
    Connect to MongoDB using the provided URI and return the client object.
    Logs an INFO message if successful; logs an ERROR on exception.
    """
    client = MongoClient(mongo_uri, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        logger.info("Pinged your deployment. Successfully connected to MongoDB!")
        return client
    except Exception as e:
        logger.error("%s error: %s", type(e).__name__, e)
        raise  # Re-raise if you want to stop execution on error

def get_pyproject_data() -> dict:
    """
    Load and return the pyproject.toml data as a dict (Python 3.11+ with tomllib).
    Adjust if you need a different path or Python version.
    """
    # This assumes pyproject.toml is at the parent level of fastapi-backend-mongo/
    pyproject_file = Path(__file__).parent / "pyproject.toml"
    with pyproject_file.open("rb") as f:
        pyproject_data = tomllib.load(f)

    return pyproject_data