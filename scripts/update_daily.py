import yfinance as yf
import requests
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
from monitoring.logging_config import setup_logging

# 配置日誌（使用 Day 2 的配置）
logger = setup_logging()

# 載入環境變數
load_dotenv()

# 資料庫配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def get_stock_ids():
    """從 stocks 表獲取當前股票代碼列表"""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT stock_id FROM stocks;")
        stock_ids = [row[0] for row in cursor.fetchall()]
        logger.info(f"Retrieved {len(stock_ids)} stock IDs from database")
        return stock_ids
    except Exception as e:
        logger.error(f"Error retrieving stock IDs: {str(e)}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_daily_prices(stock_ids):
    """使用 yfinance 更新當日股價並存入 daily_prices"""
    conn = None
    cursor = None
    try:
        today = datetime.today().strftime('%Y-%m-%d')
        logger.info(f"Fetching daily prices for {today}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        for stock_id in stock_ids:
            ticker = f"{stock_id}.TW" if stock_id != "大盤" else "^TWII"
            logger.info(f"Fetching daily data for {ticker}")
            
            # 只抓取當天的資料
            df = yf.download(ticker, start=today, end=today, progress=False)
            if df.empty:
                logger.warning(f"No data found for {ticker} on {today}")
                continue
            
            # 添加股票代碼欄位
            df['stock_id'] = stock_id
            
            # 重命名欄位
            df.columns = ['open', 'high', 'low', 'close', 'volume', 'stock_id'] if 'Adj Close' not in df.columns else ['open', 'high', 'low', 'close', 'adj_close', 'volume', 'stock_id']
            
            # 插入資料庫
            for index, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO daily_prices (date, stock_id, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, stock_id) DO NOTHING;
                """, (index.date(), row['stock_id'], row['open'], row['high'], row['low'], row['close'], int(row['volume'])))
        
        conn.commit()
        logger.info("Successfully updated daily prices for today")
    
    except Exception as e:
        logger.error(f"Error updating daily prices: {str(e)}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_stock_list():
    """使用 TWSE API 更新股票列表並存入 stocks"""
    conn = None
    cursor = None
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        logger.info("Fetching stock list from TWSE API")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data)[['Code', 'Name']]
        df.columns = ['stock_id', 'stock_name']
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 清空並插入新數據
        cursor.execute("TRUNCATE TABLE stocks;")
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO stocks (stock_id, stock_name)
                VALUES (%s, %s)
                ON CONFLICT (stock_id) DO UPDATE SET stock_name = EXCLUDED.stock_name;
            """, (row['stock_id'], row['stock_name']))
        
        conn.commit()
        logger.info(f"Successfully updated stock list with {len(df)} entries")
    
    except Exception as e:
        logger.error(f"Error updating stock list: {str(e)}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_tables():
    """創建 stocks 和 daily_prices 表格（若不存在）"""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 創建 stocks 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                stock_id VARCHAR(10) PRIMARY KEY,
                stock_name TEXT NOT NULL
            );
        """)
        
        # 創建 daily_prices 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                date DATE NOT NULL,
                stock_id VARCHAR(10) NOT NULL,
                open FLOAT,
                high FLOAT,
                low FLOAT,
                close FLOAT,
                volume BIGINT,
                PRIMARY KEY (date, stock_id)
            );
        """)
        
        conn.commit()
        logger.info("Stocks and daily_prices tables created or already exist")
    
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_all():
    """整合更新股票列表與當日股價"""
    update_stock_list()
    stock_ids = get_stock_ids()
    if stock_ids:
        update_daily_prices(stock_ids)
    else:
        logger.error("No stock IDs available to update daily prices")

if __name__ == "__main__":
    # 建立表格
    create_tables()
    
    # 執行整合更新
    update_all()