from phi.assistant import Assistant
from phi.model.xai import xAI
from phi.tools import Toolkit
from redis import Redis
from services.trading_strategies import TradingStrategies
from services.risk_management import RiskManagement
from dotenv import load_dotenv
import os
import json
from monitoring.logging_config import setup_logging
import pandas as pd
import numpy as np
import mlflow
import yfinance as yf

logger = setup_logging()
load_dotenv()

REDIS_HOST = "localhost"
redis_client = Redis(host=REDIS_HOST, port=6379, db=0)

XAI_API_KEY = os.getenv("XAI_API_KEY")
if not XAI_API_KEY:
    raise ValueError("XAI_API_KEY environment variable is not set.")

class StrategyToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="strategy_tools")
        self.trading_strategies = TradingStrategies()
        self.risk_management = RiskManagement()
        self.register(self.momentum_breakout)
        self.register(self.mean_reversion)
        self.register(self.chaos_phase_transition)
        self.register(self.llm_sentiment_trend)
        self.register(self.rlhf_volatility_arbitrage)
        self.register(self.brownian_diffusion)
        self.register(self.quantum_fluctuation)
        self.register(self.low_risk_pair_trading)
        self.register(self.lstm_momentum)
        self.register(self.sentiment_stat_arb)
        self.register(self.calculate_risk_metrics)

    def momentum_breakout(self, prices: str) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.momentum_breakout(prices)

    def mean_reversion(self, prices: str) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.mean_reversion(prices)

    def chaos_phase_transition(self, prices: str) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.chaos_phase_transition(prices)

    def llm_sentiment_trend(self, prices: str, sentiment_score: float) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.llm_sentiment_trend(prices, sentiment_score)

    def rlhf_volatility_arbitrage(self, prices: str) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.rlhf_volatility_arbitrage(prices)

    def brownian_diffusion(self, prices: str) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.brownian_diffusion(prices)

    def quantum_fluctuation(self, prices: str) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.quantum_fluctuation(prices)

    def low_risk_pair_trading(self, stock_prices: str, pair_prices: str) -> tuple:
        stock_prices = pd.Series(json.loads(stock_prices))
        pair_prices = pd.Series(json.loads(pair_prices))
        return self.trading_strategies.low_risk_pair_trading(stock_prices, pair_prices)

    def lstm_momentum(self, prices: str) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.lstm_momentum(prices)

    def sentiment_stat_arb(self, prices: str, sentiment_score: float) -> tuple:
        prices = pd.Series(json.loads(prices))
        return self.trading_strategies.sentiment_stat_arb(prices, sentiment_score)

    def calculate_risk_metrics(self, prices: str, market_prices: str) -> dict:
        prices = pd.Series(json.loads(prices))
        market_prices = pd.Series(json.loads(market_prices))
        returns = prices.pct_change().dropna()
        market_returns = market_prices.pct_change().dropna()
        return {
            "VaR": self.risk_management.calculate_var(returns),
            "Sharpe": self.risk_management.calculate_sharpe(returns),
            "Beta": self.risk_management.calculate_beta(returns, market_returns),
            "MaxDrawdown": self.risk_management.calculate_max_drawdown(prices),
            "Volatility": self.risk_management.calculate_volatility(returns),
            "CVaR": self.risk_management.calculate_cvar(returns),
            "Sortino": self.risk_management.calculate_sortino(returns),
            "JensenAlpha": self.risk_management.calculate_jensen_alpha(returns, market_returns),
            "Treynor": self.risk_management.calculate_treynor(returns, market_returns)
        }

class StrategyAgent(Assistant):
    memory_key: str = "strategy_memory"

    def __init__(self):
        toolkit = StrategyToolkit()
        super().__init__(
            name="StrategyAgent",
            model=xAI(id="grok-beta", api_key=XAI_API_KEY),
            description="Generates trading strategies with hybrid scoring",
            tools=[toolkit],
            show_tool_calls=True
        )

    def store_memory(self, data):
        try:
            redis_client.set(self.memory_key, json.dumps(data))
            logger.info(f"Stored data in Redis for {self.name}: {data}")
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")

    def read_memory(self):
        try:
            data = redis_client.get(self.memory_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error reading memory: {str(e)}")
            return None

    def generate_strategy(self, stock_id: str, transformer_pred: float, mamba_pred: float, drl_pred: float, prices: list, market_prices: list, sentiment_score: float, vix: float):
        """生成交易策略並計算混合評分"""
        try:
            prices_json = json.dumps(prices)
            market_prices_json = json.dumps(market_prices)
            prices_series = pd.Series(prices)

            # 第一層：各子策略信號與預期收益
            signals = {}
            expected_returns = {}
            signals["momentum_breakout"], expected_returns["momentum_breakout"] = self.tools[0].momentum_breakout(prices_json)
            signals["mean_reversion"], expected_returns["mean_reversion"] = self.tools[0].mean_reversion(prices_json)
            signals["chaos_phase_transition"], expected_returns["chaos_phase_transition"] = self.tools[0].chaos_phase_transition(prices_json)
            signals["llm_sentiment_trend"], expected_returns["llm_sentiment_trend"] = self.tools[0].llm_sentiment_trend(prices_json, sentiment_score)
            signals["rlhf_volatility_arbitrage"], expected_returns["rlhf_volatility_arbitrage"] = self.tools[0].rlhf_volatility_arbitrage(prices_json)
            signals["brownian_diffusion"], expected_returns["brownian_diffusion"] = self.tools[0].brownian_diffusion(prices_json)
            signals["quantum_fluctuation"], expected_returns["quantum_fluctuation"] = self.tools[0].quantum_fluctuation(prices_json)
            signals["low_risk_pair_trading"], expected_returns["low_risk_pair_trading"] = self.tools[0].low_risk_pair_trading(prices_json, market_prices_json)
            signals["lstm_momentum"], expected_returns["lstm_momentum"] = self.tools[0].lstm_momentum(prices_json)
            signals["sentiment_stat_arb"], expected_returns["sentiment_stat_arb"] = self.tools[0].sentiment_stat_arb(prices_json, sentiment_score)

            # 風險指標
            risk_metrics = self.tools[0].calculate_risk_metrics(prices_json, market_prices_json)

            # 第二層：初始權重（條件規則）
            weights = {strategy: 1.0 for strategy in signals}
            if vix > 20:
                weights["rlhf_volatility_arbitrage"] *= 1.2
                weights["quantum_fluctuation"] *= 1.2
                weights["mean_reversion"] *= 0.8
            if sentiment_score > 0.5:
                weights["llm_sentiment_trend"] *= 1.3
                weights["sentiment_stat_arb"] *= 1.3
            elif sentiment_score < -0.5:
                weights["llm_sentiment_trend"] *= 1.1
                weights["sentiment_stat_arb"] *= 1.1

            # AI 模型優化最終權重
            prompt = (
                f"Optimize weights for trading strategies based on signals, expected returns, VIX ({vix}), sentiment score ({sentiment_score}), "
                f"and risk metrics: {json.dumps(risk_metrics)}. "
                f"Signals: {json.dumps(signals)}, Expected Returns: {json.dumps(expected_returns)}, Initial Weights: {json.dumps(weights)}. "
                f"Return a JSON string with optimized weights."
            )
            response = self.run(prompt)
            response_str = "".join([chunk for chunk in response if chunk is not None])
            optimized_weights = json.loads(response_str)

            # 最終決策
            s_final = sum(optimized_weights[strategy] * signals[strategy] for strategy in signals)
            final_strategy = "buy" if s_final > 0.5 else "sell" if s_final < -0.5 else "hold"

            # 混合評分
            hybrid_score = (transformer_pred * 0.3 + mamba_pred * 0.3 + drl_pred * 0.4)

            result = {
                "stock_id": stock_id,
                "strategy": final_strategy,
                "hybrid_score": hybrid_score,
                "signals": signals,
                "optimized_weights": optimized_weights,
                "risk_metrics": risk_metrics
            }
            self.store_memory(result)

            with mlflow.start_run(run_name=f"Strategy_{stock_id}"):
                mlflow.log_param("stock_id", stock_id)
                mlflow.log_metric("transformer_pred", transformer_pred)
                mlflow.log_metric("mamba_pred", mamba_pred)
                mlflow.log_metric("drl_pred", drl_pred)
                mlflow.log_metric("hybrid_score", hybrid_score)
                mlflow.log_param("final_strategy", final_strategy)
                mlflow.log_dict({"signals": signals}, "signals.json")
                mlflow.log_dict({"weights": optimized_weights}, "weights.json")
                mlflow.log_dict({"risk_metrics": risk_metrics}, "risk_metrics.json")

            return result
        except Exception as e:
            logger.error(f"Error generating strategy: {str(e)}")
            return None

if __name__ == "__main__":
    agent = StrategyAgent()
    prices = [100, 101, 102, 103, 104]
    market_prices = [200, 201, 202, 203, 204]
    result = agent.generate_strategy("0050", 105.0, 106.0, 107.0, prices, market_prices, 0.7, 15.0)
    logger.info(f"Strategy result: {result}")