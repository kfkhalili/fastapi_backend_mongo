import os
import logging
import datetime
import requests
import fmpsdk

from fastapi import HTTPException
from dotenv import load_dotenv
from typing import List
from app.db import mongo

load_dotenv(".env.local")

FMP_API_KEY = os.getenv("FMP_API_KEY")

logger = logging.getLogger(__name__)

if not FMP_API_KEY:
    raise ValueError("No FMP_API_KEY found in environment variables!")

def company_profile_stable(apikey, symbol):
    """
    Fetches the company profile for a given stock symbol using the v4 endpoint
    of the Financial Modeling Prep API.
    
    Args:
        symbol (str): The stock symbol (e.g., 'AAPL', 'GOOG').
        apikey (str): Your FMP API key.
    
    Returns:
        dict: The company profile data in JSON format.
    """
    # The v4 endpoint for company profile
    url = f"https://financialmodelingprep.com/stable/profile?symbol={symbol}&apikey={apikey}"
    response = requests.get(url)
    response.raise_for_status()  # Raises an error for bad responses
    return response.json()

def fetch_fmp_profile(symbol: str) -> dict:
    profile_data = company_profile_stable(FMP_API_KEY, symbol=symbol)
    #profile_data = fmpsdk.company_profile(apikey=FMP_API_KEY, symbol=symbol)

    if not profile_data:
        # FMP returned empty or error
        raise HTTPException(status_code=404, detail=f"No FMP profile data found for {symbol}")

    # Usually it's a list with a single dict
    print(profile_data)
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

def get_profile(symbol: str) -> dict:
    """
    Checks MongoDB for company profile data before calling FMP's company profile endpoint.
    If the stored profile was modified on the prior Saturday, then on Sunday or Monday it won't be updated.
    Otherwise, if the data is not updated today, fresh data is fetched, upserted, and returned.
    
    Args:
        company_profiles_collection: The MongoDB collection containing profile data.
        symbol (str): The company symbol.
        
    Returns:
        dict: The company profile data.
    """
    profile_data = mongo.query_mongo_profile(symbol)
    today = datetime.datetime.utcnow().date()

    if profile_data:
        modified_at = profile_data.get("modified_at")
        mod_date = modified_at.date() if modified_at else None

        # On Sunday (weekday == 6) or Monday (weekday == 0), check if last update was on Saturday.
        if today.weekday() in (6, 0):
            last_saturday = today - datetime.timedelta(days=1) if today.weekday() == 6 else today - datetime.timedelta(days=2)
            if mod_date == last_saturday:
                # Skip updating if the latest update was last Saturday.
                return profile_data

        # On any day, if the document was updated today, return it.
        if mod_date == today:
            return profile_data

    # Either no document exists or the document is outdated; fetch fresh data.
    profile_data = fetch_fmp_profile(symbol)
    mongo.add_mongo_profile(symbol, profile_data)
    return profile_data

def get_statement(symbol: str, statement_type: str) -> List[dict]:
    """
    Fetches the requested statement_type (income, balance, or cash_flow)
    from FMP and upserts them into MongoDB.
    Returns a list of the statements.
    """
    existing = mongo.query_mongo_statement(symbol, statement_type)

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

        mongo.upsert_financial_data(symbol, doc)
        result_docs.append(doc)

    return result_docs