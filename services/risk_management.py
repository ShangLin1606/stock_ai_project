import numpy as np
import pandas as pd
import psycopg2
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging

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

class RiskManagement:
    def __init__(self):
        self.es_client = Elasticsearch(**ES_CONFIG)

    def fetch_stock_data(self, stock_id, start_date="2023-01-01", end_date="2024-08-12"):
        """從資料庫獲取股價數據"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            query = """
            SELECT date, close 
            FROM daily_prices 
            WHERE stock_id = %s AND date BETWEEN %s AND %s 
            ORDER BY date ASC;
            """
            df = pd.read_sql(query, conn, params=(stock_id, start_date, end_date))
            conn.close()
            if df.empty:
                logger.error(f"No data fetched for {stock_id}")
                return None
            df.set_index('date', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return None

    def fetch_market_data(self, start_date="2023-01-01", end_date="2024-08-12"):
        """從資料庫獲取市場數據（假設為 TWII）"""
        return self.fetch_stock_data("^TWII", start_date, end_date)

    def calculate_risk_metrics(self, stock_id, start_date="2023-01-01", end_date="2024-08-12"):
        """計算風險指標並存入 Elasticsearch"""
        stock_df = self.fetch_stock_data(stock_id, start_date, end_date)
        market_df = self.fetch_market_data(start_date, end_date)
        if stock_df is None or market_df is None:
            return None

        returns = stock_df['close'].pct_change().dropna()
        market_returns = market_df['close'].pct_change().dropna()

        metrics = {
            "VaR": self.calculate_var(returns),
            "Sharpe": self.calculate_sharpe(returns),
            "Beta": self.calculate_beta(returns, market_returns),
            "MaxDrawdown": self.calculate_max_drawdown(stock_df['close']),
            "Volatility": self.calculate_volatility(returns),
            "CVaR": self.calculate_cvar(returns),
            "Sortino": self.calculate_sortino(returns),
            "JensenAlpha": self.calculate_jensen_alpha(returns, market_returns),
            "Treynor": self.calculate_treynor(returns, market_returns)
        }

        # 風險警報與策略風險管理
        self.check_risk_alerts(stock_id, metrics)
        strategy_risk = {
            "StopLoss": self.calculate_stop_loss(stock_df['close']),
            "DynamicPositionSizing": self.calculate_dynamic_position_sizing(stock_df['close'], balance=10000),
            "RiskParity": self.calculate_risk_parity(returns, market_returns)
        }
        metrics.update(strategy_risk)

        # 存入 Elasticsearch
        doc = {
            "stock_id": stock_id,
            "date": end_date,
            "metrics": metrics,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        self.es_client.index(index=f"risk_metrics_{end_date}", id=f"{stock_id}_{end_date}", body=doc)
        logger.info(f"Stored risk metrics for {stock_id}: {metrics}")
        return metrics

    def calculate_var(self, returns, confidence_level=0.95):
        try:
            return returns.quantile(1 - confidence_level)
        except Exception as e:
            logger.error(f"Error in calculate_var: {str(e)}")
            return 0.0

    def calculate_sharpe(self, returns, risk_free_rate=0.01):
        try:
            excess_returns = returns - risk_free_rate / 252
            return excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        except Exception as e:
            logger.error(f"Error in calculate_sharpe: {str(e)}")
            return 0.0

    def calculate_beta(self, stock_returns, market_returns):
        try:
            covariance = np.cov(stock_returns, market_returns)[0, 1]
            market_variance = market_returns.var()
            return covariance / market_variance
        except Exception as e:
            logger.error(f"Error in calculate_beta: {str(e)}")
            return 0.0

    def calculate_max_drawdown(self, prices):
        try:
            roll_max = prices.cummax()
            drawdown = (prices - roll_max) / roll_max
            return drawdown.min()
        except Exception as e:
            logger.error(f"Error in calculate_max_drawdown: {str(e)}")
            return 0.0

    def calculate_volatility(self, returns):
        try:
            return returns.std() * np.sqrt(252)
        except Exception as e:
            logger.error(f"Error in calculate_volatility: {str(e)}")
            return 0.0

    def calculate_cvar(self, returns, confidence_level=0.95):
        try:
            var = self.calculate_var(returns, confidence_level)
            return returns[returns <= var].mean()
        except Exception as e:
            logger.error(f"Error in calculate_cvar: {str(e)}")
            return 0.0

    def calculate_sortino(self, returns, risk_free_rate=0.01):
        try:
            downside_returns = returns[returns < 0]
            downside_std = downside_returns.std()
            excess_returns = returns - risk_free_rate / 252
            return excess_returns.mean() / downside_std * np.sqrt(252)
        except Exception as e:
            logger.error(f"Error in calculate_sortino: {str(e)}")
            return 0.0

    def calculate_jensen_alpha(self, stock_returns, market_returns, risk_free_rate=0.01):
        try:
            beta = self.calculate_beta(stock_returns, market_returns)
            expected_return = risk_free_rate + beta * (market_returns.mean() - risk_free_rate)
            return stock_returns.mean() - expected_return
        except Exception as e:
            logger.error(f"Error in calculate_jensen_alpha: {str(e)}")
            return 0.0

    def calculate_treynor(self, stock_returns, market_returns, risk_free_rate=0.01):
        try:
            beta = self.calculate_beta(stock_returns, market_returns)
            excess_returns = stock_returns - risk_free_rate / 252
            return excess_returns.mean() / beta
        except Exception as e:
            logger.error(f"Error in calculate_treynor: {str(e)}")
            return 0.0

    # 新增策略風險管理方法
    def calculate_stop_loss(self, prices, stop_loss_percent=0.05):
        """計算止損點"""
        try:
            current_price = prices.iloc[-1]
            stop_loss_price = current_price * (1 - stop_loss_percent)
            return stop_loss_price
        except Exception as e:
            logger.error(f"Error in calculate_stop_loss: {str(e)}")
            return 0.0

    def calculate_dynamic_position_sizing(self, prices, balance=10000, risk_per_trade=0.01):
        """動態倉位管理"""
        try:
            volatility = prices.pct_change().std() * np.sqrt(252)
            risk_amount = balance * risk_per_trade
            position_size = risk_amount / (volatility * prices.iloc[-1])
            return int(position_size)
        except Exception as e:
            logger.error(f"Error in calculate_dynamic_position_sizing: {str(e)}")
            return 0

    def calculate_risk_parity(self, stock_returns, market_returns):
        """風險平價"""
        try:
            stock_vol = stock_returns.std()
            market_vol = market_returns.std()
            total_vol = stock_vol + market_vol
            weight_stock = market_vol / total_vol  # 簡單風險平價分配
            return weight_stock
        except Exception as e:
            logger.error(f"Error in calculate_risk_parity: {str(e)}")
            return 0.5

    def check_risk_alerts(self, stock_id, metrics):
        """檢查風險警報"""
        if metrics["VaR"] < -0.05:
            logger.warning(f"High VaR alert for {stock_id}: {metrics['VaR']:.4f}")
        if metrics["Volatility"] > 0.3:
            logger.warning(f"High Volatility alert for {stock_id}: {metrics['Volatility']:.4f}")
        if metrics["MaxDrawdown"] < -0.2:
            logger.warning(f"High MaxDrawdown alert for {stock_id}: {metrics['MaxDrawdown']:.4f}")

if __name__ == "__main__":
    rm = RiskManagement()
    metrics = rm.calculate_risk_metrics("0050")
    print(f"Risk Metrics for 0050: {metrics}")