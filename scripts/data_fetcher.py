import yfinance as yf
import requests
import pandas as pd
from infrastructure.database.pg_handler import PostgresHandler
from elasticsearch import Elasticsearch
import logging
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self):
        self.pg = PostgresHandler()
        self.es = Elasticsearch([f"{os.getenv('ES_HOST')}:{os.getenv('ES_PORT')}"])
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def fetch_twse_stock_info(self):
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        response = requests.get(url, headers=self.headers)
        data = response.json()
        df = pd.DataFrame(data, columns=["Code", "Name", "TradeVolume", "TradeValue", 
                                        "OpeningPrice", "HighestPrice", "LowestPrice", 
                                        "ClosingPrice", "Change", "Transaction"])
        df = df[["Code", "Name"]].rename(columns={"Code": "股號", "Name": "股名"})
        df["產業別"] = "未知"
        df.to_csv("data/processed/name_df.csv", index=False, encoding='utf-8')
        self.pg.insert_stock_info(df)
        logger.info(f"Updated stock info with {len(df)} records")

    def fetch_history(self, start_date="2020-01-01", end_date=datetime.today().strftime('%Y-%m-%d')):
        stock_ids = self.pg.get_all_stock_ids()
        for stock_id in stock_ids[:10]:  # 測試前 10 檔
            ticker = f"{stock_id}.TW"
            df = yf.download(ticker, start=start_date, end=end_date)
            if not df.empty:
                self.pg.insert_stock_prices(stock_id, df)
                self.index_to_elasticsearch(stock_id, df)
            logger.info(f"Fetched history for {stock_id}")

    def fetch_daily(self):
        stock_ids = self.pg.get_all_stock_ids()
        today = datetime.today().strftime('%Y-%m-%d')
        for stock_id in stock_ids:
            ticker = f"{stock_id}.TW"
            df = yf.download(ticker, period="1d", start=today)
            if not df.empty:
                self.pg.insert_stock_prices(stock_id, df)
                self.index_to_elasticsearch(stock_id, df)
            logger.info(f"Updated daily data for {stock_id}")

    def index_to_elasticsearch(self, stock_id, df):
        for date, row in df.iterrows():
            doc = {
                "stock_id": stock_id,
                "date": date.strftime('%Y-%m-%d'),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            }
            self.es.index(index="stock_prices", id=f"{stock_id}_{date.strftime('%Y-%m-%d')}", body=doc)

    def close(self):
        self.pg.close()