import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging
import psycopg2

logger = setup_logging()
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}
# 使用 SQLAlchemy 建立引擎

engine = psycopg2.connect(**DB_CONFIG)

class TransformerModel(nn.Module):
    def __init__(self, input_dim, d_model=64, n_heads=4, n_layers=2, dropout=0.1):
        super(TransformerModel, self).__init__()
        self.input_dim = input_dim
        self.d_model = d_model
        self.embedding = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=n_heads, dropout=dropout)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.fc_out = nn.Linear(d_model, 1)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(1, 0, 2)  # [seq_len, batch_size, d_model]
        x = self.transformer_encoder(x)
        x = x[-1, :, :]  # 取最後一個時間步
        x = self.dropout(x)
        x = self.fc_out(x)
        return x

def fetch_stock_data(stock_id):
    """從 PostgreSQL 獲取歷史股價數據"""
    try:
        query = """
        SELECT date, close FROM daily_prices 
        WHERE stock_id = %s 
        ORDER BY date ASC;
        """
        df = pd.read_sql(query, engine, params=(stock_id,))
        logger.info(f"Fetched {len(df)} days of data for stock {stock_id}")
        return df
    except Exception as e:
        logger.error(f"Error fetching stock data: {str(e)}")
        return None

def prepare_data(df, seq_length=30):
    """準備 Transformer 訓練數據"""
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df[['close']])
    
    X, y = [], []
    for i in range(len(scaled_data) - seq_length):
        X.append(scaled_data[i:i + seq_length])
        y.append(scaled_data[i + seq_length])
    
    X = np.array(X)
    y = np.array(y)
    logger.info(f"Prepared {len(X)} sequences with length {seq_length}")
    return X, y, scaler

def train_transformer(stock_id, epochs=50, batch_size=32, seq_length=30):
    """微調 Transformer 模型"""
    df = fetch_stock_data(stock_id)
    if df is None or len(df) < seq_length + 1:
        logger.error(f"Insufficient data for stock {stock_id}. Required: {seq_length + 1}, Found: {len(df) if df is not None else 0}")
        return None, None

    X, y, scaler = prepare_data(df, seq_length)
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    model = TransformerModel(input_dim=1).to(device)
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

def predict_price(model, scaler, stock_id, seq_length=30):
    """預測下一個交易日的股價"""
    df = fetch_stock_data(stock_id)
    if df is None or len(df) < seq_length:
        logger.error(f"Insufficient data for prediction on stock {stock_id}")
        return None

    last_sequence = df['close'].values[-seq_length:]
    scaled_sequence = scaler.transform(last_sequence.reshape(-1, 1))
    input_tensor = torch.FloatTensor(scaled_sequence).unsqueeze(0)  # [1, seq_length, 1]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_tensor = input_tensor.to(device)

    model.eval()
    with torch.no_grad():
        pred_scaled = model(input_tensor).cpu().numpy()
        pred_price = scaler.inverse_transform(pred_scaled)[0][0]
    
    logger.info(f"Predicted price for {stock_id}: {pred_price:.2f}")
    return pred_price

if __name__ == "__main__":
    stock_id = "0050"
    model, scaler = train_transformer(stock_id, epochs=50, seq_length=30)
    if model and scaler:
        pred_price = predict_price(model, scaler, stock_id)
        print(f"Predicted next day price for {stock_id}: {pred_price:.2f}")