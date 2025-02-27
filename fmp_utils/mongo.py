import os
import logging
import fmpsdk

from fastapi import HTTPException
from dotenv import load_dotenv
from pymongo import UpdateOne
from typing import Optional, List

load_dotenv(".env.local")

MONGODB_URI = os.getenv("MONGODB_URI")
FMP_API_KEY = os.getenv("FMP_API_KEY")

logger = logging.getLogger(__name__)

if not MONGODB_URI:
    raise ValueError("No MONGODB_URI found in environment variables!")
if not FMP_API_KEY:
    raise ValueError("No FMP_API_KEY found in environment variables!")

def query_mongo_profile(collection, symbol: str) -> Optional[dict]:
    return collection.find_one({"symbol": symbol})

def query_mongo_statement(collection, symbol: str, statement_type: str) -> Optional[dict]:
    # Build the Mongo query for financial statements
    query = {"symbol": symbol}
    if statement_type:
        query["statementType"] = statement_type

    # Attempt to find existing statements in Mongo
    return list(collection.find(query))

def fetch_fmp_profile(symbol: str) -> dict:
    profile_data = fmpsdk.company_profile(apikey=FMP_API_KEY, symbol=symbol)

    if not profile_data:
        # FMP returned empty or error
        raise HTTPException(status_code=404, detail=f"No FMP profile data found for {symbol}")

    # Usually it's a list with a single dict
    return profile_data[0]

def fetch_fmp_statement(symbol: str, statement_type: str) -> dict:
    # The fmpsdk has separate calls for each statement type
    if statement_type == "income":
        statements = fmpsdk.income_statement(apikey=FMP_API_KEY, symbol=symbol, limit=5)
    elif statement_type == "balance":
        statements = fmpsdk.balance_sheet_statement(apikey=FMP_API_KEY, symbol=symbol, limit=5)
    elif statement_type == "cash_flow":
        statements = fmpsdk.cash_flow_statement(apikey=FMP_API_KEY, symbol=symbol, limit=5)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid statementType: {statement_type}")

    if not statements:
        raise HTTPException(status_code=404, detail=f"No FMP data for {statement_type} of {symbol}")
    
    return statements

def upsert_symbol_data(collection, symbol: str, data: dict) -> None:
    collection.update_one(
        {"symbol": symbol},
        {"$set": data},
        upsert=True
    )

def get_profile(company_profiles_collection, symbol: str) -> dict:
    """
    Checks Mongo for data before calling FMP's company profile endpoint
    If fetching from FMP, upserts into MongoDB.
    Returns the profile as a dictionary.
    """
    profile_data = query_mongo_profile(company_profiles_collection, symbol)

    if profile_data:
        return profile_data
    
    profile_data = fetch_fmp_profile(symbol)
    
    upsert_symbol_data(company_profiles_collection, symbol, profile_data)

    return profile_data

def upsert_financial_data(collection, symbol: str, doc: str) -> None:
        # Define unique query for upsert
        query = {
            "symbol": symbol,
            "statementType": doc["statementType"],
            "fiscalYear": doc["fiscalYear"],
            "period": doc["period"]
        }

        # Upsert the entire doc
        collection.update_one(query, {"$set": doc}, upsert=True)

def get_statement(financial_statements_collection, symbol: str, statement_type: str) -> List[dict]:
    """
    Fetches the requested statement_type (income, balance, or cash_flow)
    from FMP and upserts them into MongoDB.
    Returns a list of the statements.
    """
    existing = query_mongo_statement(financial_statements_collection, symbol, statement_type)

    if existing:
        return existing
    
    data_list = fetch_fmp_statement(symbol, statement_type)

    result_docs = []

    for record in data_list:
        # Convert the fmpsdk record (which is a dict) to a new dict so we can modify it
        doc = dict(record)  # copy all fields (raw data)
        doc["symbol"] = symbol
        doc["statementType"] = statement_type

        # Optional: Extract or standardize certain fields
        # e.g. "calendarYear" => int
        calendar_year = record.get("calendarYear")
        if calendar_year and calendar_year.isdigit():
            doc["fiscalYear"] = int(calendar_year)
        else:
            doc["fiscalYear"] = None

        upsert_financial_data(financial_statements_collection, symbol, doc)
        result_docs.append(doc)

    return result_docs