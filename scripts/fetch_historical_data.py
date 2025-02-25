import yfinance as yf
import pandas as pd
from src.infrastructure.database.pg_handler import PostgresHandler
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_historical_stock_data(start_date="2010-01-01", end_date="2025-02-24"):
    pg = PostgresHandler()
    stocks = pg.get_all_stocks_from_name_df()
    
    for stock_id in stocks:
        ticker = f"{stock_id}.TW"
        try:
            logger.info(f"Fetching data for {ticker}")
            df = yf.download(ticker, start=start_date, end=end_date)
            if df.empty:
                logger.warning(f"No data found for {ticker}")
                continue
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            pg.insert_stock_data(stock_id, df)
            logger.info(f"Successfully fetched and stored data for {ticker}")
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
    
    pg.close()
    logger.info("Historical stock data fetching completed")

def initialize_stock_info():
    pg = PostgresHandler()
    df = pd.read_csv('data/name_df.csv', encoding='utf-8')
    pg.insert_stock_info(df)
    pg.close()
    logger.info("Stock info initialized from name_df.csv")

if __name__ == "__main__":
    initialize_stock_info()
    fetch_historical_stock_data()