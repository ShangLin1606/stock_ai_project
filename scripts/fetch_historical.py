import yfinance as yf
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging

# 配置日誌
logger = setup_logging()

# 載入環境變數
load_dotenv()

# 資料庫配置字典
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def load_stock_ids_from_db():
    """從資料庫的 stocks 表格讀取股票代碼"""
    stock_ids = []
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # 假設 stocks 表格有一個欄位叫做 stock_id 儲存股票代碼
                cur.execute("SELECT stock_id FROM stocks")
                rows = cur.fetchall()
                for row in rows:
                    stock_ids.append(row[0])  # 取出 stock_id 欄位的值
        logger.info(f"從資料庫載入 {len(stock_ids)} 個股票代碼")
        return stock_ids
    except Exception as e:
        logger.error(f"從資料庫載入股票代碼時發生錯誤: {str(e)}")
        return []

def fetch_historical(stock_ids, start_date="2000-01-01"):
    """
    抓取多個股票的歷史股價並存入 PostgreSQL
    :param stock_ids: 股票代碼列表
    :param start_date: 開始日期（預設 2000-01-01）
    """
    for stock_id in stock_ids:
        try:
            ticker = f"{stock_id}.TW" if stock_id != "大盤" else "^TWII"
            logger.info(f"正在從 {start_date} 開始抓取 {ticker} 的歷史資料")
            
            # 使用 yfinance 抓取資料
            df = yf.download(ticker, start=start_date, progress=False)
            if df.empty:
                logger.warning(f"找不到 {ticker} 的資料")
                continue
            
            # 添加股票代碼欄位
            df['stock_id'] = stock_id
            
            # 重命名欄位
            df.columns = ['open', 'high', 'low', 'close', 'volume', 'stock_id'] if 'Adj Close' not in df.columns else ['open', 'high', 'low', 'close', 'adj_close', 'volume', 'stock_id']
            
            # 重設索引，將日期作為普通列
            df = df.reset_index()
            
            # 使用 psycopg2 連接到數據庫
            with psycopg2.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cur:
                    # 準備插入語句
                    insert_query = """
                        INSERT INTO daily_prices (date, stock_id, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date, stock_id) DO NOTHING
                    """
                    # 將 DataFrame 數據轉為元組列表
                    data = [tuple(row) for row in df[['Date', 'stock_id', 'open', 'high', 'low', 'close', 'volume']].values]
                    # 批量插入
                    cur.executemany(insert_query, data)
                conn.commit()
            logger.info(f"成功儲存 {ticker} 的歷史資料")
        
        except Exception as e:
            logger.error(f"抓取 {ticker} 資料時發生錯誤: {str(e)}")

def create_table():
    """創建歷史股價表格（若不存在）"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""
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
        logger.info("歷史股價表格已建立或已存在")
    except Exception as e:
        logger.error(f"建立表格時發生錯誤: {str(e)}")

if __name__ == "__main__":
    # 建立表格
    create_table()
    
    # 從資料庫載入股票代碼
    stock_ids = load_stock_ids_from_db()
    
    # 抓取所有股票歷史股價
    if stock_ids:
        fetch_historical(stock_ids)
    else:
        logger.error("沒有可用的股票代碼來抓取歷史資料")