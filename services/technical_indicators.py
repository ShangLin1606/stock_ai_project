import pandas as pd
import numpy as np
import psycopg2
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

class TechnicalIndicators:
    def __init__(self):
        pass

    def fetch_stock_data(self, stock_id, start_date="2023-01-01", end_date="2024-08-12"):
        """從 PostgreSQL 資料庫獲取股價數據"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            query = """
            SELECT date, open, high, low, close, volume 
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
            df.columns = [col.capitalize() for col in df.columns]
            return df
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return None

    def calculate(self, stock_id, indicator, **kwargs):
        """計算指定技術指標"""
        df = self.fetch_stock_data(stock_id)
        if df is None:
            return 0.0

        method = getattr(self, f"calculate_{indicator.lower()}", None)
        if method is None:
            logger.error(f"Indicator {indicator} not implemented")
            return 0.0

        try:
            return method(df, **kwargs)
        except Exception as e:
            logger.error(f"Error calculating {indicator}: {str(e)}")
            return 0.0

    def calculate_sma(self, df, period=20):
        """簡單移動平均線"""
        return df['Close'].rolling(window=period).mean().iloc[-1]

    def calculate_ema(self, df, period=20):
        """指數移動平均線"""
        return df['Close'].ewm(span=period, adjust=False).mean().iloc[-1]

    def calculate_rsi(self, df, period=14):
        """相對強弱指數"""
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]

    def calculate_stochastic(self, df, k_period=14, d_period=3):
        """隨機震盪指標"""
        low_min = df['Low'].rolling(window=k_period).min()
        high_max = df['High'].rolling(window=k_period).max()
        k = 100 * (df['Close'] - low_min) / (high_max - low_min)
        d = k.rolling(window=d_period).mean()
        return k.iloc[-1], d.iloc[-1]

    def calculate_macd(self, df, fast=12, slow=26, signal=9):
        """移動平均收斂發散"""
        ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]

    def calculate_bollinger_bands(self, df, period=20, std_dev=2):
        """布林帶"""
        sma = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        return upper.iloc[-1], sma.iloc[-1], lower.iloc[-1]

    def calculate_atr(self, df, period=14):
        """平均真實範圍"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean().iloc[-1]

    def calculate_cci(self, df, period=20):
        """商品通道指數"""
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
        return (tp - sma_tp).iloc[-1] / (0.015 * mad.iloc[-1])

    def calculate_momentum(self, df, period=10):
        """動量"""
        return df['Close'].iloc[-1] - df['Close'].shift(period).iloc[-1]

    def calculate_roc(self, df, period=10):
        """變動率"""
        return ((df['Close'] - df['Close'].shift(period)) / df['Close'].shift(period) * 100).iloc[-1]

    def calculate_std(self, df, period=20):
        """標準差"""
        return df['Close'].rolling(window=period).std().iloc[-1]

    def calculate_williams_r(self, df, period=14):
        """威廉指標"""
        high_max = df['High'].rolling(window=period).max()
        low_min = df['Low'].rolling(window=period).min()
        return -100 * (high_max - df['Close']) / (high_max - low_min).iloc[-1]

    def calculate_vwma(self, df, period=20):
        """成交量加權移動平均"""
        return (df['Close'] * df['Volume']).rolling(window=period).sum() / df['Volume'].rolling(window=period).sum().iloc[-1]

    def calculate_ad_line(self, df):
        """累積/派發線"""
        mfm = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
        mfv = mfm * df['Volume']
        return mfv.cumsum().iloc[-1]

    def calculate_obv(self, df):
        """能量潮"""
        obv = pd.Series(0, index=df.index)
        obv[df['Close'] > df['Close'].shift(1)] = df['Volume']
        obv[df['Close'] < df['Close'].shift(1)] = -df['Volume']
        return obv.cumsum().iloc[-1]

    def calculate_donchian_channel(self, df, period=20):
        """唐奇安通道"""
        upper = df['High'].rolling(window=period).max()
        lower = df['Low'].rolling(window=period).min()
        return upper.iloc[-1], lower.iloc[-1]

    def calculate_keltner_channel(self, df, period=20, atr_period=10, multiplier=2):
        """肯特納通道"""
        ema = df['Close'].ewm(span=period, adjust=False).mean()
        atr = self.calculate_atr(df, atr_period)
        upper = ema + multiplier * atr
        lower = ema - multiplier * atr
        return upper.iloc[-1], ema.iloc[-1], lower.iloc[-1]

    def calculate_adx(self, df, period=14):
        """平均方向指數"""
        tr = pd.concat([df['High'] - df['Low'], np.abs(df['High'] - df['Close'].shift()), np.abs(df['Low'] - df['Close'].shift())], axis=1).max(axis=1)
        dm_plus = (df['High'] - df['High'].shift()).where((df['High'] - df['High'].shift()) > (df['Low'].shift() - df['Low']), 0)
        dm_minus = (df['Low'].shift() - df['Low']).where((df['Low'].shift() - df['Low']) > (df['High'] - df['High'].shift()), 0)
        atr = tr.rolling(window=period).mean()
        di_plus = 100 * dm_plus.rolling(window=period).mean() / atr
        di_minus = 100 * dm_minus.rolling(window=period).mean() / atr
        dx = 100 * np.abs(di_plus - di_minus) / (di_plus + di_minus)
        return dx.rolling(window=period).mean().iloc[-1]

    def calculate_psar(self, df, af_start=0.02, af_increment=0.02, af_max=0.2):
        """拋物線 SAR"""
        psar = df['Close'].copy()
        bullish = True
        ep = df['Low'].iloc[0]
        af = af_start
        for i in range(1, len(df)):
            if bullish:
                psar.iloc[i] = psar.iloc[i-1] + af * (ep - psar.iloc[i-1])
                if df['Low'].iloc[i] < psar.iloc[i]:
                    bullish = False
                    psar.iloc[i] = ep
                    ep = df['High'].iloc[i]
                    af = af_start
                else:
                    if df['High'].iloc[i] > ep:
                        ep = df['High'].iloc[i]
                        af = min(af + af_increment, af_max)
            else:
                psar.iloc[i] = psar.iloc[i-1] + af * (ep - psar.iloc[i-1])
                if df['High'].iloc[i] > psar.iloc[i]:
                    bullish = True
                    psar.iloc[i] = ep
                    ep = df['Low'].iloc[i]
                    af = af_start
                else:
                    if df['Low'].iloc[i] < ep:
                        ep = df['Low'].iloc[i]
                        af = min(af + af_increment, af_max)
        return psar.iloc[-1]

    def calculate_aroon(self, df, period=25):
        """阿隆指標"""
        aroon_up = 100 * (df['High'].rolling(window=period).apply(lambda x: x.argmax()) + 1) / period
        aroon_down = 100 * (df['Low'].rolling(window=period).apply(lambda x: x.argmin()) + 1) / period
        return aroon_up.iloc[-1], aroon_down.iloc[-1]

    def calculate_ichimoku(self, df):
        """一目均衡表 (簡化版：轉換線與基準線)"""
        tenkan_sen = (df['High'].rolling(window=9).max() + df['Low'].rolling(window=9).min()) / 2
        kijun_sen = (df['High'].rolling(window=26).max() + df['Low'].rolling(window=26).min()) / 2
        return tenkan_sen.iloc[-1], kijun_sen.iloc[-1]

def test_indicators():
    ti = TechnicalIndicators()
    stock_id = "0050"
    indicators = [
        "SMA", "EMA", "RSI", "Stochastic", "MACD", "Bollinger_Bands",
        "ATR", "CCI", "Momentum", "ROC", "STD", "Williams_R",
        "VWMA", "AD_Line", "OBV", "Donchian_Channel", "Keltner_Channel",
        "ADX", "PSAR", "Aroon", "Ichimoku"
    ]

    for indicator in indicators:
        if indicator == "Stochastic":
            k, d = ti.calculate(stock_id, indicator)
            logger.info(f"{indicator}: %K = {k:.2f}, %D = {d:.2f}")
        elif indicator == "MACD":
            macd, signal, hist = ti.calculate(stock_id, indicator)
            logger.info(f"{indicator}: MACD = {macd:.2f}, Signal = {signal:.2f}, Histogram = {hist:.2f}")
        elif indicator == "Bollinger_Bands":
            upper, middle, lower = ti.calculate(stock_id, indicator)
            logger.info(f"{indicator}: Upper = {upper:.2f}, Middle = {middle:.2f}, Lower = {lower:.2f}")
        elif indicator == "Donchian_Channel":
            upper, lower = ti.calculate(stock_id, indicator)
            logger.info(f"{indicator}: Upper = {upper:.2f}, Lower = {lower:.2f}")
        elif indicator == "Keltner_Channel":
            upper, middle, lower = ti.calculate(stock_id, indicator)
            logger.info(f"{indicator}: Upper = {upper:.2f}, Middle = {middle:.2f}, Lower = {lower:.2f}")
        elif indicator == "Aroon":
            up, down = ti.calculate(stock_id, indicator)
            logger.info(f"{indicator}: Aroon Up = {up:.2f}, Aroon Down = {down:.2f}")
        elif indicator == "Ichimoku":
            tenkan, kijun = ti.calculate(stock_id, indicator)
            logger.info(f"{indicator}: Tenkan-sen = {tenkan:.2f}, Kijun-sen = {kijun:.2f}")
        else:
            result = ti.calculate(stock_id, indicator)
            logger.info(f"{indicator}: {result:.2f}")

if __name__ == "__main__":
    test_indicators()