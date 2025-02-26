import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

class PostgresHandler:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            # 股票資訊表（已存在）
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    stock_id VARCHAR(10) PRIMARY KEY,
                    stock_name TEXT NOT NULL,
                    industry TEXT
                );
            """)
            # 歷史股價表（已存在）
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    id SERIAL PRIMARY KEY,
                    stock_id VARCHAR(10),
                    date DATE,
                    open_price DECIMAL,
                    high_price DECIMAL,
                    low_price DECIMAL,
                    close_price DECIMAL,
                    volume BIGINT,
                    FOREIGN KEY (stock_id) REFERENCES stock_info(stock_id),
                    UNIQUE (stock_id, date)
                );
            """)
            # 新增財報表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS financial_reports (
                    id SERIAL PRIMARY KEY,
                    stock_id VARCHAR(10),
                    year INTEGER,
                    quarter INTEGER,
                    revenue DECIMAL,
                    eps DECIMAL,
                    FOREIGN KEY (stock_id) REFERENCES stock_info(stock_id),
                    UNIQUE (stock_id, year, quarter)
                );
            """)
            self.conn.commit()

    def insert_stock_info(self, df):
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO stock_info (stock_id, stock_name, industry)
                VALUES %s
                ON CONFLICT (stock_id) DO NOTHING;
            """, df[['股號', '股名', '產業別']].values.tolist())
            self.conn.commit()

    def insert_stock_data(self, stock_id, df):
        data = [
            (stock_id, date.strftime('%Y-%m-%d'), row['Open'], row['High'],
             row['Low'], row['Close'], int(row['Volume']))
            for date, row in df.iterrows()
        ]
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO stock_prices (stock_id, date, open_price, high_price, low_price, close_price, volume)
                VALUES %s
                ON CONFLICT (stock_id, date) DO NOTHING;
            """, data)
            self.conn.commit()

    def insert_financial_report(self, stock_id, df):
        data = [
            (stock_id, int(row['year']), int(row['quarter']), float(row['revenue']), float(row['eps']))
            for _, row in df.iterrows()
        ]
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO financial_reports (stock_id, year, quarter, revenue, eps)
                VALUES %s
                ON CONFLICT (stock_id, year, quarter) DO NOTHING;
            """, data)
            self.conn.commit()

    def get_all_stocks_from_name_df(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT stock_id FROM stock_info;")
            return [row[0] for row in cur.fetchall()]

    def get_stock_prices(self, stock_id, start_date, end_date):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT date, close_price
                FROM stock_prices
                WHERE stock_id = %s AND date BETWEEN %s AND %s
                ORDER BY date;
            """, (stock_id, start_date, end_date))
            return pd.DataFrame(cur.fetchall(), columns=['date', 'close_price']).set_index('date')

    def close(self):
        self.conn.close()