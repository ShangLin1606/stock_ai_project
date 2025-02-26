import requests
import pandas as pd
from src.infrastructure.database.pg_handler import PostgresHandler
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockInfoCrawler:
    def __init__(self):
        self.pg = PostgresHandler()
        self.output_csv = 'data/name_df.csv'
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_twse_stock_info(self, retries=3, delay=5):
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json"
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                stocks = data.get("data", [])
                if not stocks:
                    raise ValueError("No data returned from TWSE API")
                df = pd.DataFrame(stocks, columns=[
                    "股號", "股名", "成交股數", "成交金額", "開盤價", 
                    "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"
                ])
                df = df[["股號", "股名"]].copy()
                df["產業別"] = "未知"
                logger.info(f"Fetched {len(df)} stocks from TWSE")
                return df
            except (requests.RequestException, ValueError) as e:
                logger.error(f"Attempt {attempt + 1} failed for TWSE: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    logger.warning("Failed to fetch TWSE data after retries, returning empty DataFrame")
                    return pd.DataFrame(columns=["股號", "股名", "產業別"])

    def update_stock_info(self):
        logger.info("Starting daily stock info update (TWSE only)")
        twse_df = self.fetch_twse_stock_info()
        
        if twse_df.empty:
            logger.error("No stock info fetched from TWSE")
            return
        
        # 去除重複的股號，保留第一筆記錄
        combined_df = twse_df.drop_duplicates(subset=["股號"], keep='first')
        logger.info(f"After deduplication, {len(combined_df)} unique stocks remain")
        
        combined_df.to_csv(self.output_csv, index=False, encoding='utf-8')
        logger.info(f"Updated {self.output_csv} with {len(combined_df)} stocks")
        
        self.pg.insert_stock_info(combined_df)
        logger.info("Synchronized stock info to PostgreSQL")

    def close(self):
        self.pg.close()

if __name__ == "__main__":
    crawler = StockInfoCrawler()
    try:
        crawler.update_stock_info()
    except Exception as e:
        logger.error(f"Update failed: {str(e)}")
    finally:
        crawler.close()