# main.py

import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import get_mongo_client


# Load environment variables from .env.local
load_dotenv(".env.local")

# Retrieve MongoDB URI from environment
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("No MONGODB_URI found in environment variables!")

# Initialize the FastAPI app
app = FastAPI()

# Create a MongoDB client and specify the database/collection
client = get_mongo_client(MONGODB_URI)
db = client["fmp"]
collection = db["traded_list"]

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
