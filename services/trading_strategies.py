import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import psycopg2
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging
from services.risk_management import RiskManagement

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

class LSTM(nn.Module):
    def __init__(self, input_size=1, hidden_size=50, num_layers=2):
        super(LSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

class TradingStrategies:
    def __init__(self):
        self.risk_manager = RiskManagement()

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
            return df['close']
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return None

    def momentum_breakout(self, stock_id, window=20):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        high = prices.rolling(window=window).max()
        low = prices.rolling(window=window).min()
        current_price = prices.iloc[-1]
        if current_price > high.iloc[-2]:
            return 1, 0.02
        elif current_price < low.iloc[-2]:
            return -1, -0.02
        return 0, 0.0

    def mean_reversion(self, stock_id, window=20):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        mean = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        current_price = prices.iloc[-1]
        if current_price < mean.iloc[-1] - std.iloc[-1]:
            return 1, 0.015
        elif current_price > mean.iloc[-1] + std.iloc[-1]:
            return -1, -0.015
        return 0, 0.0

    def chaos_phase_transition(self, stock_id, window=20):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        volatility = prices.pct_change().rolling(window=window).std()
        trend = prices.diff().rolling(window=window).mean()
        if volatility.iloc[-1] > volatility.mean() * 1.5:
            return 0, 0.0
        elif trend.iloc[-1] > 0:
            return 1, 0.01
        else:
            return -1, -0.01

    def llm_sentiment_trend(self, stock_id, sentiment_score):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        trend = prices.pct_change().rolling(window=10).mean()
        if sentiment_score > 0.5 and trend.iloc[-1] > 0:
            return 1, 0.025
        elif sentiment_score < -0.5 and trend.iloc[-1] < 0:
            return -1, -0.025
        return 0, 0.0

    def rlhf_volatility_arbitrage(self, stock_id, window=20):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        vol = prices.pct_change().rolling(window=window).std()
        if vol.iloc[-1] > vol.mean() * 1.2:
            return 1, 0.01
        elif vol.iloc[-1] < vol.mean() * 0.8:
            return -1, -0.01
        return 0, 0.0

    def brownian_diffusion(self, stock_id, window=20):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        smoothed = prices.ewm(span=window).mean()
        if prices.iloc[-1] > smoothed.iloc[-1]:
            return 1, 0.015
        elif prices.iloc[-1] < smoothed.iloc[-1]:
            return -1, -0.015
        return 0, 0.0

    def quantum_fluctuation(self, stock_id, window=20):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        probs = np.random.normal(0, 1, len(prices))
        signal = 1 if probs[-1] > 1 else -1 if probs[-1] < -1 else 0
        return signal, 0.01 if signal != 0 else 0.0

    def low_risk_pair_trading(self, stock_id, pair_stock_id):
        stock_prices = self.fetch_stock_data(stock_id)
        pair_prices = self.fetch_stock_data(pair_stock_id)
        if stock_prices is None or pair_prices is None:
            return 0, 0.0
        spread = stock_prices - pair_prices
        mean_spread = spread.rolling(window=20).mean()
        std_spread = spread.rolling(window=20).std()
        if spread.iloc[-1] > mean_spread.iloc[-1] + std_spread.iloc[-1]:
            return -1, -0.01
        elif spread.iloc[-1] < mean_spread.iloc[-1] - std_spread.iloc[-1]:
            return 1, 0.01
        return 0, 0.0

    def lstm_momentum(self, stock_id, window=20):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        model = LSTM()
        X = prices.values[:-1].reshape(-1, 1, 1)
        y = prices.values[1:].reshape(-1, 1)
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        for _ in range(10):
            pred = model(X_tensor)
            loss = nn.MSELoss()(pred, y_tensor)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        pred = model(X_tensor[-1:].reshape(1, 1, 1)).item()
        if pred > prices.iloc[-1]:
            return 1, 0.02
        else:
            return -1, -0.02
        return 0, 0.0

    def sentiment_stat_arb(self, stock_id, sentiment_score):
        prices = self.fetch_stock_data(stock_id)
        if prices is None:
            return 0, 0.0
        mean = prices.rolling(window=20).mean()
        if sentiment_score > 0.5 and prices.iloc[-1] < mean.iloc[-1]:
            return 1, 0.015
        elif sentiment_score < -0.5 and prices.iloc[-1] > mean.iloc[-1]:
            return -1, -0.015
        return 0, 0.0

    def backtest_strategy(self, strategy_func, stock_id, sentiment_score=None, pair_stock_id=None, start_date="2023-01-01", end_date="2024-08-12"):
        """回測策略並記錄績效與風險指標至 Elasticsearch"""
        es_client = Elasticsearch(**ES_CONFIG)
        prices = self.fetch_stock_data(stock_id, start_date, end_date)
        if prices is None:
            return None

        balance = 10000
        shares = 0
        trades = []
        risk_metrics = self.risk_manager.calculate_risk_metrics(stock_id, start_date, end_date)

        for i in range(1, len(prices)):
            kwargs = {"stock_id": stock_id}
            if sentiment_score is not None:
                kwargs["sentiment_score"] = sentiment_score
            if pair_stock_id:
                kwargs["pair_stock_id"] = pair_stock_id

            signal, expected_return = strategy_func(**kwargs)
            current_price = prices.iloc[i]
            stop_loss = risk_metrics["StopLoss"]

            # 應用止損
            if shares > 0 and current_price < stop_loss:
                shares = 0
                balance += current_price
                trades.append(("stop_loss_sell", current_price, prices.index[i]))
                continue

            # 動態倉位管理
            position_size = risk_metrics["DynamicPositionSizing"]
            if signal == 1 and balance >= current_price * position_size:
                shares += position_size
                balance -= current_price * position_size
                trades.append(("buy", current_price, prices.index[i]))
            elif signal == -1 and shares >= position_size:
                shares -= position_size
                balance += current_price * position_size
                trades.append(("sell", current_price, prices.index[i]))

        final_value = balance + shares * prices.iloc[-1]
        returns = (final_value - 10000) / 10000
        performance = {
            "total_return": returns,
            "trades": len(trades),
            "max_drawdown": risk_metrics["MaxDrawdown"],
            "volatility": risk_metrics["Volatility"]
        }

        doc = {
            "stock_id": stock_id,
            "strategy": strategy_func.__name__,
            "start_date": start_date,
            "end_date": end_date,
            "performance": performance,
            "risk_metrics": risk_metrics,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        es_client.index(index=f"strategy_performance_{end_date}", id=f"{stock_id}_{strategy_func.__name__}", body=doc)
        logger.info(f"Backtest for {stock_id} - {strategy_func.__name__}: {performance}")
        return performance

if __name__ == "__main__":
    ts = TradingStrategies()
    strategies = [
        ts.momentum_breakout,
        ts.mean_reversion,
        ts.chaos_phase_transition,
        lambda stock_id: ts.llm_sentiment_trend(stock_id, 0.7),
        ts.rlhf_volatility_arbitrage,
        ts.brownian_diffusion,
        ts.quantum_fluctuation,
        lambda stock_id: ts.low_risk_pair_trading(stock_id, "0056"),
        ts.lstm_momentum,
        lambda stock_id: ts.sentiment_stat_arb(stock_id, 0.7)
    ]
    for strategy in strategies:
        perf = ts.backtest_strategy(strategy, "0050")
        print(f"{strategy.__name__}: {perf}")