import pytest
from fastapi.testclient import TestClient
from src.presentation.api.views.api_views import app
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@pytest.fixture
def client():
    logger.info("Initializing TestClient")
    return TestClient(app)

def test_get_all_stocks(client):
    response = client.get("/stocks")
    assert response.status_code == 200
    stocks = response.json()
    assert len(stocks) > 0, "No stocks returned"
    assert "stock_id" in stocks[0], "Missing stock_id in response"

def test_get_stock_prices(client):
    response = client.get("/stocks/2330/prices?start_date=2024-01-01&end_date=2025-02-26")
    assert response.status_code == 200
    prices = response.json()
    assert len(prices) > 0, "No prices returned"
    assert "close_price" in prices[0], "Missing close_price in response"

def test_get_stock_prices_not_found(client):
    logger.info("Testing get_stock_prices_not_found")
    response = client.get("/stocks/9999/prices?start_date=2024-01-01&end_date=2025-02-26")
    logger.info(f"Response status: {response.status_code}, content: {response.text}")
    assert response.status_code == 404
    assert "detail" in response.json()