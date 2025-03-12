import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging

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

def import_name_df():
    """將 name_df.csv 導入 PostgreSQL"""
    conn = None
    cursor = None
    try:
        df = pd.read_csv('data/raw/name_df.csv')
        df = df[['股號', '股名']]  # 假設欄位為 '股號' 和 '股名'
        df.columns = ['stock_id', 'stock_name']
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 清空並插入數據
        cursor.execute("TRUNCATE TABLE stocks;")
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO stocks (stock_id, stock_name)
                VALUES (%s, %s)
                ON CONFLICT (stock_id) DO UPDATE SET stock_name = EXCLUDED.stock_name;
            """, (row['stock_id'], row['stock_name']))
        
        conn.commit()
        logger.info(f"Successfully imported {len(df)} stocks from name_df.csv")
    
    except Exception as e:
        logger.error(f"Error importing name_df.csv: {str(e)}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    # 假設 stocks 表已由 update_daily.py 建立，這裡直接導入
    import_name_df()