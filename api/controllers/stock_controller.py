import pandas as pd
import psycopg2
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging
from datetime import date  # 新增

logger = setup_logging()
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

ES_CONFIG = {
    "hosts": ["http://localhost:9200"],
    "basic_auth": (os.getenv("ES_USERNAME", "elastic"), os.getenv("ES_PASSWORD", "P@ssw0rd"))
}

class StockController:
    def __init__(self):
        self.es_client = Elasticsearch(**ES_CONFIG)

    def fetch_daily_prices(self, stock_id, start_date, end_date):
        """從 PostgreSQL 獲取每日股價數據"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            query = """
            SELECT date, open, high, low, close, volume 
            FROM daily_prices 
            WHERE stock_id = %s AND date BETWEEN %s AND %s 
            ORDER BY date ASC;
            """
            df = pd.read_sql(query, con=conn, params=(stock_id, start_date, end_date))
            conn.close()
            if df.empty:
                logger.warning(f"No price data found for {stock_id} between {start_date} and {end_date}")
                return None
            # 將 date 欄位轉為 ISO 字串
            df['date'] = df['date'].apply(lambda x: x.isoformat() if isinstance(x, date) else x)
            return df.to_dict(orient="records")
        except Exception as e:
            logger.error(f"Error fetching daily prices: {str(e)}")
            return None

    def fetch_sentiment_data(self, stock_id, start_date, end_date):
        """從 Elasticsearch 獲取情緒數據"""
        try:
            query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"stock_id": stock_id}},
                            {"range": {"date": {"gte": start_date, "lte": end_date}}}
                        ]
                    }
                }
            }
            response = self.es_client.search(index=f"sentiment_analysis_*", body=query)
            hits = response["hits"]["hits"]
            if not hits:
                logger.warning(f"No sentiment data found for {stock_id} between {start_date} and {end_date}")
                return None
            sentiments = [hit["_source"] for hit in hits]
            # 確保 sentiment 中的 date 欄位是字串
            for sentiment in sentiments:
                if 'date' in sentiment and isinstance(sentiment['date'], date):
                    sentiment['date'] = sentiment['date'].isoformat()
            return sentiments
        except Exception as e:
            logger.error(f"Error fetching sentiment data: {str(e)}")
            return None

    def fetch_risk_metrics(self, stock_id, start_date, end_date):
        """從 Elasticsearch 獲取風險指標"""
        try:
            query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"stock_id": stock_id}},
                            {"range": {"date": {"gte": start_date, "lte": end_date}}}
                        ]
                    }
                }
            }
            response = self.es_client.search(index=f"risk_metrics_*", body=query)
            hits = response["hits"]["hits"]
            if not hits:
                logger.warning(f"No risk metrics found for {stock_id} between {start_date} and {end_date}")
                return None
            metrics = [hit["_source"]["metrics"] for hit in hits]
            return metrics[-1]
        except Exception as e:
            logger.error(f"Error fetching risk metrics: {str(e)}")
            return None

    def get_stock_data(self, stock_id, start_date, end_date):
        """整合股價、情緒和風險數據"""
        prices = self.fetch_daily_prices(stock_id, start_date, end_date)
        sentiments = self.fetch_sentiment_data(stock_id, start_date, end_date)
        risk_metrics = self.fetch_risk_metrics(stock_id, start_date, end_date)

        if not prices and not sentiments and not risk_metrics:
            return None

        latest_price = prices[-1] if prices else None
        response = {
            "stock_id": stock_id,
            "latest_price": latest_price,
            "daily_prices": prices if prices else [],
            "sentiments": sentiments if sentiments else [],
            "risk_metrics": risk_metrics if risk_metrics else {}
        }
        return response