# main.py

import os
import fmpsdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
from utils import get_mongo_client
from fmp_utils import mongo

# Load environment variables from .env.local
load_dotenv(".env.local")

# Retrieve MongoDB URI from environment
MONGODB_URI = os.getenv("MONGODB_URI")
FMP_API_KEY = os.getenv("FMP_API_KEY")
if not MONGODB_URI:
    raise ValueError("No MONGODB_URI found in environment variables!")
if not FMP_API_KEY:
    raise ValueError("No FMP_API_KEY found in environment variables!")

# Initialize the FastAPI app
app = FastAPI()

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a MongoDB client and specify the database/collection
client = get_mongo_client(MONGODB_URI)
db = client["fmp"]

collection = db["traded_list"]
company_profiles_collection = db["company_profiles"]
financial_statements_collection = db["financial_statements"]

# Example Pydantic model for creating items
class Item(BaseModel):
    symbol: str
    exchange: str
    exchangeShortName: str
    name: str
    type: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Poetry + FastAPI + MongoDB example!"}

@app.get("/items")
def get_items():
    """
    Retrieve all items from the MongoDB collection.
    """
    items = list(collection.find({}))
    # Convert ObjectId to string for JSON serialization
    for item in items:
        item["_id"] = str(item["_id"])
    return items

@app.get("/items/{item}")
def get_item(item: str):
    """
    Retrieve a single item by its symbol.
    """
    item = collection.find_one({"symbol": item})
    if item:
        item["_id"] = str(item["_id"])
        return item
    return {"error": "Item not found"}

@app.post("/items")
def create_item(item: Item):
    """
    Create a new item in the collection.
    """
    result = collection.insert_one(item.dict())
    created_item = collection.find_one({"_id": result.inserted_id})
    if created_item:
        created_item["_id"] = str(created_item["_id"])
    return created_item

@app.get("/profiles/{symbol}")
def get_company_profile(symbol: str) -> dict:
    doc = dict(mongo.get_profile(company_profiles_collection, symbol))

    if("_id" in doc):
        doc["_id"] = str(doc["_id"])

    return doc

@app.get("/financials/{symbol}")
def get_financials(
    symbol: str,
    statement_type: Optional[str] = None
) -> List:
    """
    Fetch the company financial statements, 
    optionally filtered by statement type.
    
    Example usage:
        GET /financials/AAPL
        GET /financials/AAPL?statement_type=income
        GET /financials/AAPL?statement_type=balance
    """
    if statement_type:
        # Fetch just the requested statement type
        statement_docs = mongo.get_statement(financial_statements_collection, symbol, statement_type)
    else:
        # statement_type not given => fetch all 3 types
        all_types = ["income", "balance", "cash_flow"]
        statement_docs = []
        for stype in all_types:
            statement_docs.extend(mongo.get_statement(financial_statements_collection, symbol, stype))

    # Convert _id field to string for fastAPI compatibility
    for doc in statement_docs:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])

    # Return response
    return statement_docs