from infrastructure.database.pg_handler import PostgresHandler
from api.models.stock_model import StockInfo, StockPrice
from typing import List
import logging

logger = logging.getLogger(__name__)

class StockController:
    def __init__(self):
        self.pg = PostgresHandler()

    def get_all_stocks(self) -> List[StockInfo]:
        with self.pg.engine.connect() as conn:
            df = pd.read_sql("SELECT stock_id, stock_name, industry FROM stock_info;", conn)
        return [StockInfo(**row) for _, row in df.iterrows()]

    def get_stock_prices(self, stock_id: str, start_date: str, end_date: str) -> List[StockPrice]:
        with self.pg.engine.connect() as conn:
            df = pd.read_sql(
                "SELECT date, open_price, high_price, low_price, close_price, volume "
                "FROM stock_prices WHERE stock_id = %s AND date BETWEEN %s AND %s ORDER BY date;",
                conn, params=(stock_id, start_date, end_date)
            )
        return [StockPrice(**row) for _, row in df.iterrows()]

    def close(self):
        self.pg.close()