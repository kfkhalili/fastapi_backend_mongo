# main.py

import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from dotenv import load_dotenv
from app.db import mongo
from app.integrations import fmp
from app.models.schemas import *

# Load environment variables from .env.local
load_dotenv(".env.local")

# Retrieve MongoDB URI from environment
FMP_API_KEY = os.getenv("FMP_API_KEY")
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

@app.get("/")
def read_root():
    return {"message": "Welcome to the Poetry + FastAPI + MongoDB example!"}

@app.get("/items")
def get_items():
    """
    Retrieve all items from the MongoDB collection.
    """
    items = mongo.get_traded_items()
    # Convert ObjectId to string for JSON serialization
    for item in items:
        item["_id"] = str(item["_id"])
    return items

@app.get("/items/{item}")
def get_item(item: str):
    """
    Retrieve a single item by its symbol.
    """
    item = mongo.get_traded_items(item)
    if item:
        item["_id"] = str(item["_id"])
        return item
    return {"error": "Item not found"}

@app.post("/items")
def create_item(item: Item):
    """
    Create a new item in the collection.
    """
    created_item = mongo.insert_traded_item(item.dict())
    if created_item:
        created_item["_id"] = str(created_item["_id"])
    return created_item

@app.get("/profiles/{symbol}")
def get_company_profile(symbol: str) -> dict:
    doc = dict(fmp.get_profile(symbol))

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
        statement_docs = fmp.get_statement(symbol, statement_type)
    else:
        # statement_type not given => fetch all 3 types
        all_types = ["income", "balance", "cash_flow"]
        statement_docs = []
        for stype in all_types:
            statement_docs.extend(fmp.get_statement(symbol, stype))

    # Convert _id field to string for fastAPI compatibility
    for doc in statement_docs:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])

    # Return response
    return statement_docs

@app.post("/user_input", status_code=status.HTTP_201_CREATED)
async def push_user_input(
    user_input: dict
) -> dict:
    """
    Store user input
    """
    try:
        mongo.push_user_input(user_input)
        return {"message": "User input stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user_input", response_model=dict)
def get_user_input() -> dict:
    """
    Retrieve all user inputs stored in the database.
    """
    try:
        doc = mongo.get_user_input()
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))