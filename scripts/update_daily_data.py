import yfinance as yf
from src.infrastructure.database.pg_handler import PostgresHandler
from dotenv import load_dotenv
import logging
import os
from datetime import datetime

load_dotenv()

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_daily_stock_data():
    pg = PostgresHandler()
    stocks = pg.get_all_stocks_from_name_df()
    today = datetime.today().strftime('%Y-%m-%d')
    
    for stock_id in stocks:
        ticker = f"{stock_id}.TW"
        try:
            logger.info(f"Updating daily data for {ticker}")
            df = yf.download(ticker, period="1d", start=today)
            if df.empty:
                logger.warning(f"No data found for {ticker} today")
                continue
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            pg.insert_stock_data(stock_id, df)
            logger.info(f"Successfully updated data for {ticker}")
        except Exception as e:
            logger.error(f"Error updating data for {ticker}: {str(e)}")
    
    pg.close()
    logger.info("Daily stock data update completed")

if __name__ == "__main__":
    update_daily_stock_data()