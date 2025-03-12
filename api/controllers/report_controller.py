from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

ES_CONFIG = {
    "hosts": ["http://localhost:9200"],
    "basic_auth": (os.getenv("ES_USERNAME", "elastic"), os.getenv("ES_PASSWORD", "P@ssw0rd"))
}

class ReportController:
    def __init__(self):
        self.es_client = Elasticsearch(**ES_CONFIG)

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
                return None
            return [hit["_source"] for hit in hits]
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
                return None
            return [hit["_source"]["metrics"] for hit in hits][-1]
        except Exception as e:
            logger.error(f"Error fetching risk metrics: {str(e)}")
            return None

    def generate_report(self, stock_id, start_date, end_date):
        """生成投資報告"""
        sentiments = self.fetch_sentiment_data(stock_id, start_date, end_date)
        risk_metrics = self.fetch_risk_metrics(stock_id, start_date, end_date)

        if not sentiments and not risk_metrics:
            return None

        # 簡單報告生成邏輯
        latest_sentiment = sentiments[-1]["sentiment"] if sentiments else "neutral"
        volatility = risk_metrics["Volatility"] if risk_metrics else 0.0
        mdd = risk_metrics["MaxDrawdown"] if risk_metrics else 0.0

        report = {
            "stock_id": stock_id,
            "period": f"{start_date} to {end_date}",
            "summary": (
                f"Investment Report for {stock_id}:\n"
                f"Latest Sentiment: {latest_sentiment}\n"
                f"Volatility: {volatility:.2f}\n"
                f"Max Drawdown: {mdd:.2f}\n"
                f"Recommendation: {'Hold' if volatility > 0.3 else 'Consider Buy' if latest_sentiment == 'positive' else 'Consider Sell'}"
            )
        }
        return report