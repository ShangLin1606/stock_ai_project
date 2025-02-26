import pytest
from src.infrastructure.database.pg_handler import PostgresHandler
from src.infrastructure.crawler.stock_info_crawler import StockInfoCrawler
import pandas as pd

@pytest.fixture
def pg_handler():
    pg = PostgresHandler()
    with pg.conn.cursor() as cur:
        cur.execute("TRUNCATE stock_info, stock_prices RESTART IDENTITY;")
        pg.conn.commit()
    yield pg
    pg.close()

@pytest.fixture
def stock_crawler():
    crawler = StockInfoCrawler()
    yield crawler
    crawler.close()

def test_insert_stock_info(pg_handler):
    df = pd.DataFrame({
        '股號': ['2330'],
        '股名': ['台積電'],
        '產業別': ['半導體']
    })
    pg_handler.insert_stock_info(df)
    with pg_handler.conn.cursor() as cur:
        cur.execute("SELECT * FROM stock_info WHERE stock_id = '2330';")
        result = cur.fetchone()
    assert result == ('2330', '台積電', '半導體')

def test_insert_stock_data(pg_handler):
    df = pd.DataFrame({
        'Open': [500.0], 'High': [510.0], 'Low': [495.0], 'Close': [505.0], 'Volume': [1000000]
    }, index=[pd.Timestamp('2023-01-01')])
    pg_handler.insert_stock_data('2330', df)
    with pg_handler.conn.cursor() as cur:
        cur.execute("SELECT open_price, close_price FROM stock_prices WHERE stock_id = '2330' AND date = '2023-01-01';")
        result = cur.fetchone()
    assert result == (500.0, 505.0)

def test_get_latest_stock_data(pg_handler):
    df = pd.DataFrame({
        'Open': [600.0], 'High': [610.0], 'Low': [595.0], 'Close': [605.0], 'Volume': [2000000]
    }, index=[pd.Timestamp('2023-01-02')])
    pg_handler.insert_stock_data('2330', df)
    with pg_handler.conn.cursor() as cur:
        cur.execute("SELECT close_price FROM stock_prices WHERE stock_id = '2330' ORDER BY date DESC LIMIT 1;")
        result = cur.fetchone()
    assert result is not None, "No data returned from query"
    assert result[0] == 605.0

def test_update_stock_info(stock_crawler):
    stock_crawler.update_stock_info()
    df = pd.read_csv(stock_crawler.output_csv, encoding='utf-8')
    assert len(df) > 1000, f"Expected over 1000 stocks from TWSE, got {len(df)}"
    with stock_crawler.pg.conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM stock_info;")
        count = cur.fetchone()[0]
    assert count > 1000, f"Expected over 1000 records in stock_info, got {count}"