import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from mamba_ssm import Mamba
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

class MambaModel(nn.Module):
    def __init__(self, input_dim, d_model=64, d_state=16, d_conv=4, expand=2, dropout=0.1):
        super(MambaModel, self).__init__()
        self.input_dim = input_dim
        self.d_model = d_model
        self.embedding = nn.Linear(input_dim, d_model)
        self.mamba = Mamba(
            d_model=d_model,
            d_state=d_state,
            d_conv=d_conv,
            expand=expand
        )
        self.fc_out = nn.Linear(d_model, 1)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.embedding(x)  # [batch_size, seq_len, d_model]
        x = self.mamba(x)      # [batch_size, seq_len, d_model]
        x = x[:, -1, :]        # 取最後一個時間步
        x = self.dropout(x)
        x = self.fc_out(x)
        return x

def fetch_stock_and_sentiment_data(stock_id, sentiment_data):
    """從 PostgreSQL 獲取股價數據並結合情緒分數"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        query = """
        SELECT date, close FROM daily_prices 
        WHERE stock_id = %s 
        ORDER BY date ASC;
        """
        df = pd.read_sql(query, conn, params=(stock_id,))
        conn.close()
        logger.info(f"Fetched {len(df)} days of price data for stock {stock_id}")

        if len(df) == 0:
            logger.warning(f"No price data found for stock {stock_id}")
            return None

        sentiment_df = pd.DataFrame(sentiment_data, columns=["date", "sentiment"])
        sentiment_df["date"] = pd.to_datetime(sentiment_df["date"])
        sentiment_df["sentiment_score"] = sentiment_df["sentiment"].map({"positive": 1, "neutral": 0, "negative": -1})

        df["date"] = pd.to_datetime(df["date"])
        df = df.merge(sentiment_df[["date", "sentiment_score"]], on="date", how="left").fillna(0)
        logger.info(f"Combined {len(df)} days of data with sentiment for stock {stock_id}")
        return df
    except Exception as e:
        logger.error(f"Error fetching stock data: {str(e)}")
        return None

def prepare_data(df, seq_length=30):
    """準備 Mamba 訓練數據，包含情緒分數"""
    scaler = MinMaxScaler()
    scaled_prices = scaler.fit_transform(df[['close']])
    sentiment_scores = df['sentiment_score'].values.reshape(-1, 1)

    X, y = [], []
    for i in range(len(scaled_prices) - seq_length):
        price_seq = scaled_prices[i:i + seq_length]
        sentiment_seq = sentiment_scores[i:i + seq_length]
        X.append(np.hstack((price_seq, sentiment_seq)))
        y.append(scaled_prices[i + seq_length])
    
    X = np.array(X)
    y = np.array(y)
    logger.info(f"Prepared {len(X)} sequences with length {seq_length}")
    return X, y, scaler

def train_mamba(stock_id, sentiment_data, epochs=50, batch_size=32, seq_length=30):
    """訓練 Mamba 模型"""
    df = fetch_stock_and_sentiment_data(stock_id, sentiment_data)
    if df is None or len(df) < seq_length + 1:
        logger.error(f"Insufficient data for stock {stock_id}")
        return None, None

    X, y, scaler = prepare_data(df, seq_length)
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    model = MambaModel(input_dim=2).to(device)  # 2 = price + sentiment
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    X_train = torch.FloatTensor(X_train).to(device)
    y_train = torch.FloatTensor(y_train).to(device)
    X_test = torch.FloatTensor(X_test).to(device)
    y_test = torch.FloatTensor(y_test).to(device)

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        output = model(X_train)
        loss = criterion(output, y_train)
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                test_output = model(X_test)
                test_loss = criterion(test_output, y_test)
            logger.info(f"Epoch {epoch+1}/{epochs}, Train Loss: {loss.item():.4f}, Test Loss: {test_loss.item():.4f}")

    return model, scaler

def predict_price_with_sentiment(model, scaler, stock_id, sentiment_data, seq_length=30):
    """預測下一個交易日的股價，考慮情緒"""
    df = fetch_stock_and_sentiment_data(stock_id, sentiment_data)
    if df is None or len(df) < seq_length:
        logger.error(f"Insufficient data for prediction on stock {stock_id}")
        return None

    last_sequence = df[['close', 'sentiment_score']].values[-seq_length:]
    scaled_sequence = np.copy(last_sequence)
    scaled_sequence[:, 0] = scaler.transform(last_sequence[:, 0].reshape(-1, 1))[:, 0]  # 只縮放 close
    input_tensor = torch.FloatTensor(scaled_sequence).unsqueeze(0)  # [1, seq_length, 2]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_tensor = input_tensor.to(device)

    model.eval()
    with torch.no_grad():
        pred_scaled = model(input_tensor).cpu().numpy()
        pred_price = scaler.inverse_transform(pred_scaled)[0][0]
    
    logger.info(f"Predicted price for {stock_id} with sentiment: {pred_price:.2f}")
    return pred_price

if __name__ == "__main__":
    stock_id = "0050"
    sentiment_data = [
        {"date": "2024-08-10", "sentiment": "positive"},
        {"date": "2024-08-11", "sentiment": "neutral"},
        {"date": "2024-08-12", "sentiment": "positive"}
    ]
    model, scaler = train_mamba(stock_id, sentiment_data, epochs=50, seq_length=30)
    if model and scaler:
        pred_price = predict_price_with_sentiment(model, scaler, stock_id, sentiment_data)
        print(f"Predicted next day price for {stock_id}: {pred_price:.2f}")