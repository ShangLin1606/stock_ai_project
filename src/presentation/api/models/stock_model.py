from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class StockInfo(BaseModel):
    stock_id: str
    stock_name: str
    industry: Optional[str] = None

class StockPrice(BaseModel):
    date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int