from src.infrastructure.database.pg_handler import PostgresHandler
from src.presentation.api.models.stock_model import StockInfo, StockPrice
from typing import List
import logging
import psycopg2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockController:
    def __init__(self):
        try:
            self.pg = PostgresHandler()
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {str(e)}")
            raise

    def get_all_stocks(self) -> List[StockInfo]:
        try:
            with self.pg.conn.cursor() as cur:
                cur.execute("SELECT stock_id, stock_name, industry FROM stock_info;")
                results = [StockInfo(stock_id=row[0], stock_name=row[1], industry=row[2]) for row in cur.fetchall()]
            logger.info(f"Fetched {len(results)} stocks from database")
            return results
        except Exception as e:
            logger.error(f"Error fetching all stocks: {str(e)}")
            return []

    def get_stock_prices(self, stock_id: str, start_date: str, end_date: str) -> List[StockPrice]:
        try:
            with self.pg.conn.cursor() as cur:
                cur.execute("""
                    SELECT date, open_price, high_price, low_price, close_price, volume
                    FROM stock_prices
                    WHERE stock_id = %s AND date BETWEEN %s AND %s
                    ORDER BY date;
                """, (stock_id, start_date, end_date))
                rows = cur.fetchall()
                if not rows:
                    logger.info(f"No price records found for {stock_id}")
                    return []
                results = [
                    StockPrice(
                        date=row[0],
                        open_price=float(row[1]),
                        high_price=float(row[2]),
                        low_price=float(row[3]),
                        close_price=float(row[4]),
                        volume=int(row[5])
                    ) for row in rows
                ]
            logger.info(f"Fetched {len(results)} price records for {stock_id}")
            return results
        except Exception as e:
            logger.error(f"Error fetching prices for {stock_id}: {str(e)}")
            return []

    def close(self):
        self.pg.close()