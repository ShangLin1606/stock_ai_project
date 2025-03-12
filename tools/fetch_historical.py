import yfinance as yf
from monitoring.logging_config import setup_logging

logger = setup_logging()

def fetch_historical(stock_id, period="1y"):
    """從 yfinance 獲取歷史股價數據"""
    try:
        ticker = f"{stock_id}.TW" if stock_id != "大盤" else "^TWII"
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            logger.warning(f"No historical data found for {stock_id}")
            return None
        logger.info(f"Fetched {len(df)} days of historical data for {stock_id}")
        return df
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        return None

if __name__ == "__main__":
    stock_id = "0050"
    df = fetch_historical(stock_id)
    if df is not None:
        print(df.tail())