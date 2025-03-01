from fastapi import FastAPI, HTTPException
from api.controllers.stock_controller import StockController
from api.models.stock_model import StockInfo, StockPrice
from typing import List
from contextlib import asynccontextmanager

app = FastAPI()
controller = StockController()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    controller.close()

app = FastAPI(lifespan=lifespan)

@app.get("/stocks", response_model=List[StockInfo])
async def get_all_stocks():
    stocks = controller.get_all_stocks()
    if not stocks:
        raise HTTPException(status_code=404, detail="No stocks found")
    return stocks

@app.get("/stocks/{stock_id}/prices", response_model=List[StockPrice])
async def get_stock_prices(stock_id: str, start_date: str, end_date: str):
    prices = controller.get_stock_prices(stock_id, start_date, end_date)
    if not prices:
        raise HTTPException(status_code=404, detail="No price data found")
    return prices