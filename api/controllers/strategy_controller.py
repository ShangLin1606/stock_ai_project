import pandas as pd
from elasticsearch import Elasticsearch
from services.trading_strategies import TradingStrategies
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

ES_CONFIG = {
    "hosts": ["http://localhost:9200"],
    "basic_auth": (os.getenv("ES_USERNAME", "elastic"), os.getenv("ES_PASSWORD", "P@ssw0rd"))
}

class StrategyController:
    def __init__(self):
        self.es_client = Elasticsearch(**ES_CONFIG)
        self.trading_strategies = TradingStrategies()

    def fetch_performance_data(self, stock_id, start_date, end_date):
        """從 Elasticsearch 獲取策略績效數據"""
        try:
            query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"stock_id": stock_id}},
                            {"range": {"end_date": {"gte": start_date, "lte": end_date}}}
                        ]
                    }
                }
            }
            response = self.es_client.search(index=f"strategy_performance_*", body=query)
            hits = response["hits"]["hits"]
            if not hits:
                return None
            return [hit["_source"] for hit in hits]
        except Exception as e:
            logger.error(f"Error fetching performance data: {str(e)}")
            return None

    def generate_strategy_suggestion(self, stock_id, start_date, end_date):
        """生成交易策略建議"""
        performance_data = self.fetch_performance_data(stock_id, start_date, end_date)
        if not performance_data:
            signal, expected_return = self.trading_strategies.momentum_breakout(stock_id)
            strategy = "momentum_breakout"
            total_return = expected_return
        else:
            best_strategy = max(performance_data, key=lambda x: x["performance"]["total_return"])
            strategy = best_strategy["strategy"]
            total_return = best_strategy["performance"]["total_return"]
            signal = 1 if total_return > 0 else -1 if total_return < 0 else 0

        suggestion = {
            "stock_id": stock_id,
            "strategy": strategy,
            "signal": "buy" if signal == 1 else "sell" if signal == -1 else "hold",
            "expected_return": total_return,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        return suggestion