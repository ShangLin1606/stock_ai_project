import pytest
from src.infrastructure.database.pg_handler import PostgresHandler
import pandas as pd

@pytest.fixture
def pg_handler():
    pg = PostgresHandler()
    yield pg
    pg.close()

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