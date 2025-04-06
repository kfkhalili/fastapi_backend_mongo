import os
import logging

from dotenv import load_dotenv
from typing import Optional
from pymongo.errors import PyMongoError
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

logger = logging.getLogger(__name__)

load_dotenv(".env.local")

MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in environment variables! Add your MONGODB_URI to .env.local and try again.")

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

client = get_mongo_client(MONGODB_URI)
db = client["fmp"]
collection = db["traded_list"]
user_input_collection = db["user_inputs"]
company_profiles_collection = db["company_profiles"]
financial_statements_collection = db["financial_statements"]

def upsert_symbol_data(collection, symbol: str, data: dict) -> None:
    collection.update_one(
        {"symbol": symbol},
        {
            "$set": data,
            "$currentDate": {"modified_at": {"$type": "date"}}
        },
        upsert=True
    )

def get_traded_items(item = None):
    if item:
        return collection.find_one({"symbol": item})
    else:
        return list(collection.find({}))
    
def insert_traded_item(item):
    result = collection.insert_one(item)
    return collection.find_one({"_id": result.inserted_id})

def push_user_input(user_input: dict) -> str:
    """
    Merges new user input into the existing document in the 'user_inputs' collection.
    New fields will overwrite older ones if they already exist.
    If no document exists, it inserts a new one.
    Returns the document's ID as a string.
    """
    try:
        existing_doc = get_user_input()
        if existing_doc and '_id' in existing_doc:
            # Merge the new fields into the existing document
            user_input_collection.update_one(
                {'_id': existing_doc['_id']},
                {"$set": user_input}
            )
            return str(existing_doc['_id'])
        else:
            result = user_input_collection.insert_one(user_input)
            return str(result.inserted_id)
    except PyMongoError as error:
        raise Exception(f"Error updating user input: {error}")

def get_user_input() -> dict:
    """
    Retrieves the first user input from the 'user_inputs' collection.
    Returns the document as a dictionary if it exists, or None if the collection is empty.
    """
    try:
        # Fetch all documents from the collection
        user_inputs = list(user_input_collection.find())
        return user_inputs[0] if user_inputs else {}
    except PyMongoError as error:
        raise Exception(f"Error retrieving user input: {error}")  
    
def query_mongo_profile(symbol: str) -> Optional[dict]:
    return company_profiles_collection.find_one({"symbol": symbol})

def add_mongo_profile(symbol: str, data: dict):
    upsert_symbol_data(company_profiles_collection, symbol, data)

def query_mongo_statement(symbol: str, statement_type: str) -> Optional[dict]:
    # Build the Mongo query for financial statements
    query = {"symbol": symbol}
    if statement_type:
        query["statementType"] = statement_type

    # Attempt to find existing statements in Mongo
    return list(financial_statements_collection.find(query))

def upsert_financial_data(symbol: str, doc: str) -> None:
        # Define unique query for upsert
        query = {
            "symbol": symbol,
            "statementType": doc["statementType"],
            "fiscalYear": doc["fiscalYear"],
            "period": doc["period"]
        }

        # Upsert the entire doc
        financial_statements_collection.update_one(query, {"$set": doc}, upsert=True)