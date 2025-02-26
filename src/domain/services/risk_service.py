import pandas as pd
import numpy as np
from scipy.stats import norm
from src.infrastructure.database.pg_handler import PostgresHandler
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RiskService:
    def __init__(self):
        self.pg = PostgresHandler()
        self.market_id = "0050"
        self.risk_free_rate = 0.01
        self.days = 252

    def get_prices(self, stock_id, start_date="2024-01-01", end_date="2025-02-26"):
        df = self.pg.get_stock_prices(stock_id, start_date, end_date)
        if df.empty:
            logger.warning(f"No price data for {stock_id}")
            return None
        df['close_price'] = df['close_price'].astype(float)
        return df['close_price']

    def calculate_var(self, stock_id, confidence_level=0.95):
        prices = self.get_prices(stock_id)
        if prices is None:
            return None
        returns = prices.pct_change().dropna()
        mean = returns.mean()
        std = returns.std()
        # 調整為負值，表示損失
        var = -norm.ppf(confidence_level, mean, std) * np.sqrt(self.days) * prices.iloc[-1]
        logger.info(f"VaR for {stock_id}: {var:.2f}")
        return var

    def calculate_sharpe_ratio(self, stock_id):
        prices = self.get_prices(stock_id)
        if prices is None:
            return None
        returns = prices.pct_change().dropna()
        excess_returns = returns - (self.risk_free_rate / self.days)
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(self.days)
        logger.info(f"Sharpe Ratio for {stock_id}: {sharpe:.2f}")
        return sharpe

    def calculate_beta(self, stock_id):
        stock_prices = self.get_prices(stock_id)
        market_prices = self.get_prices(self.market_id)
        if stock_prices is None or market_prices is None:
            return None
        aligned_data = pd.concat([stock_prices, market_prices], axis=1, join='inner')
        stock_returns = aligned_data.iloc[:, 0].pct_change().dropna()
        market_returns = aligned_data.iloc[:, 1].pct_change().dropna()
        covariance = np.cov(stock_returns, market_returns)[0, 1]
        market_variance = market_returns.var()
        beta = covariance / market_variance if market_variance != 0 else 0
        logger.info(f"Beta for {stock_id}: {beta:.2f}")
        return beta

    def calculate_max_drawdown(self, stock_id):
        prices = self.get_prices(stock_id)
        if prices is None:
            return None
        roll_max = prices.cummax()
        drawdowns = (prices - roll_max) / roll_max
        max_drawdown = drawdowns.min()
        logger.info(f"Max Drawdown for {stock_id}: {max_drawdown:.2%}")
        return max_drawdown

    def calculate_volatility(self, stock_id):
        prices = self.get_prices(stock_id)
        if prices is None:
            return None
        returns = prices.pct_change().dropna()
        volatility = returns.std() * np.sqrt(self.days)
        logger.info(f"Volatility for {stock_id}: {volatility:.2%}")
        return volatility

    def calculate_cvar(self, stock_id, confidence_level=0.95):
        prices = self.get_prices(stock_id)
        if prices is None:
            return None
        returns = prices.pct_change().dropna()
        var_percentile = returns.quantile(1 - confidence_level)
        cvar = returns[returns <= var_percentile].mean() * prices.iloc[-1]
        # CVaR 應為負值（損失）
        cvar = -cvar if cvar > 0 else cvar
        logger.info(f"CVaR for {stock_id}: {cvar:.2f}")
        return cvar

    def calculate_sortino_ratio(self, stock_id):
        prices = self.get_prices(stock_id)
        if prices is None:
            return None
        returns = prices.pct_change().dropna()
        excess_returns = returns - (self.risk_free_rate / self.days)
        downside_returns = excess_returns[excess_returns < 0]
        downside_std = downside_returns.std() if not downside_returns.empty else 0
        sortino = excess_returns.mean() / downside_std * np.sqrt(self.days) if downside_std != 0 else 0
        logger.info(f"Sortino Ratio for {stock_id}: {sortino:.2f}")
        return sortino

    def calculate_jensen_alpha(self, stock_id):
        stock_prices = self.get_prices(stock_id)
        market_prices = self.get_prices(self.market_id)
        if stock_prices is None or market_prices is None:
            return None
        aligned_data = pd.concat([stock_prices, market_prices], axis=1, join='inner')
        stock_returns = aligned_data.iloc[:, 0].pct_change().dropna()
        market_returns = aligned_data.iloc[:, 1].pct_change().dropna()
        beta = self.calculate_beta(stock_id)
        if beta is None:
            return None
        expected_return = (self.risk_free_rate / self.days) + beta * (market_returns.mean() - self.risk_free_rate / self.days)
        alpha = stock_returns.mean() - expected_return
        logger.info(f"Jensen's Alpha for {stock_id}: {alpha:.4f}")
        return alpha

    def calculate_treynor_ratio(self, stock_id):
        stock_prices = self.get_prices(stock_id)
        market_prices = self.get_prices(self.market_id)
        if stock_prices is None or market_prices is None:
            return None
        aligned_data = pd.concat([stock_prices, market_prices], axis=1, join='inner')
        stock_returns = aligned_data.iloc[:, 0].pct_change().dropna()
        beta = self.calculate_beta(stock_id)
        if beta is None or beta == 0:
            return None
        excess_returns = stock_returns - (self.risk_free_rate / self.days)
        treynor = excess_returns.mean() / beta * self.days
        logger.info(f"Treynor Ratio for {stock_id}: {treynor:.2f}")
        return treynor

    def analyze_risk(self, stock_ids):
        results = {}
        for stock_id in stock_ids:
            results[stock_id] = {
                "VaR": self.calculate_var(stock_id),
                "Sharpe": self.calculate_sharpe_ratio(stock_id),
                "Beta": self.calculate_beta(stock_id),
                "MaxDrawdown": self.calculate_max_drawdown(stock_id),
                "Volatility": self.calculate_volatility(stock_id),
                "CVaR": self.calculate_cvar(stock_id),
                "Sortino": self.calculate_sortino_ratio(stock_id),
                "JensenAlpha": self.calculate_jensen_alpha(stock_id),
                "Treynor": self.calculate_treynor_ratio(stock_id)
            }
        return results

    def close(self):
        self.pg.close()

if __name__ == "__main__":
    risk_service = RiskService()
    stocks = risk_service.pg.get_all_stocks_from_name_df()[:5]
    results = risk_service.analyze_risk(stocks)
    for stock_id, metrics in results.items():
        print(f"{stock_id}: {metrics}")
    risk_service.close()