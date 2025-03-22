# setup_mongo.py

import os
import logging
import fmpsdk
import pandas as pd

from dotenv import load_dotenv
from pymongo import UpdateOne
from app.utils import get_mongo_client
from app.logging_config import setup_logging

setup_logging()

# Load environment variables from .env.local
load_dotenv(".env.local")

# Retrieve MongoDB URI from environment
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("No MONGODB_URI found in environment variables!")

FMP_API_KEY = os.getenv("FMP_API_KEY")
if not FMP_API_KEY:
    raise ValueError("No FMP_API_KEY found in environment variables!")

logging.basicConfig(level=logging.INFO)

# Use your helper to connect
client = get_mongo_client(MONGODB_URI)
db = client["fmp"]
collection = db["traded_list"]

# Create a unique index on "symbol" if not already present
collection.create_index([("symbol", 1)], name="symbol_unique_idx", unique=True)

logging.info("Database 'fmp' and collection 'traded_list' created or verified.")
logging.info("Unique index on 'symbol' created or verified.")

df_available = pd.DataFrame(fmpsdk.available_traded_list(apikey=FMP_API_KEY))
df_xetra = df_available.drop(columns=["price"])
records = df_xetra.to_dict("records")

# Create a function that maps a record to an UpdateOne operation
def record_to_upsert(doc):
    return UpdateOne(
        {"symbol": doc["symbol"]},  # query
        {"$set": doc},             # update
        upsert=True
    )

# Build the list of upsert operations
operations = list(map(record_to_upsert, records))

# Execute the bulk upsert
try:
    result = client.fmp.traded_list.bulk_write(operations, ordered=False)
    logging.info(
        f"Matched: {result.matched_count}, "
        f"Modified: {result.modified_count}, "
        f"Upserted: {result.upserted_count}"
    )
except Exception as e:
    logging.error("Bulk upsert error:", e)