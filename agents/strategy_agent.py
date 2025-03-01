from phidata.agent import Agent
import pandas as pd
import numpy as np
from scipy.stats import norm
from infrastructure.database.pg_handler import PostgresHandler

class StrategyAgent(Agent):
    def __init__(self):
        super().__init__(name="StrategyAgent")
        self.pg = PostgresHandler()
        self.risk_free_rate = 0.01
        self.days = 252

    def get_prices(self, stock_id):
        df = self.pg.get_stock_prices(stock_id, "2024-01-01", "2025-03-01")
        return df['close_price'].astype(float) if not df.empty else None

    def calculate_var(self, stock_id, confidence_level=0.95):
        prices = self.get_prices(stock_id)
        if prices is None:
            return None
        returns = prices.pct_change().dropna()
        return -norm.ppf(confidence_level, returns.mean(), returns.std()) * np.sqrt(self.days) * prices.iloc[-1]

    # 其他風險指標（略，參考 RiskService）

    def generate_strategy(self, stock_id, prediction_data, sentiment_data):
        risks = {
            "VaR": self.calculate_var(stock_id),
            # 其他指標
        }
        strategy = "Buy" if prediction_data["prediction"] > 0 else "Hold"  # 簡化邏輯
        score = 0.25 * risks["VaR"] + 0.25 * sentiment_data["sentiment"] + 0.25 * prediction_data["prediction"]
        return {"strategy": strategy, "score": score}

    def close(self):
        self.pg.close()