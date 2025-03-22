from pydantic import BaseModel

# Example Pydantic model for creating items
class Item(BaseModel):
    symbol: str
    exchange: str
    exchangeShortName: str
    name: str
    type: str