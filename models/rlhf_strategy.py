import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging
import mlflow
import ray
from openrlhf.cli.train_ppo_ray import train

logger = setup_logging()
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

class StockTradingEnv:
    def __init__(self, stock_id, sentiment_data, seq_length=30):
        self.stock_id = stock_id
        self.sentiment_data = pd.DataFrame(sentiment_data, columns=["date", "sentiment"])
        self.sentiment_data["date"] = pd.to_datetime(self.sentiment_data["date"])
        self.sentiment_data["sentiment_score"] = self.sentiment_data["sentiment"].map({"positive": 1, "neutral": 0, "negative": -1})
        self.seq_length = seq_length
        self.data = self._fetch_data()
        self.current_step = seq_length
        self.balance = 10000
        self.shares = 0
        self.max_steps = len(self.data) - seq_length - 1
        self.done = False

    def _fetch_data(self):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            query = "SELECT date, close FROM daily_prices WHERE stock_id = %s ORDER BY date ASC;"
            df = pd.read_sql(query, conn, params=(self.stock_id,))
            conn.close()
            df["date"] = pd.to_datetime(df["date"])
            df = df.merge(self.sentiment_data[["date", "sentiment_score"]], on="date", how="left").fillna(0)
            return df
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return pd.DataFrame()

    def reset(self):
        self.current_step = self.seq_length
        self.balance = 10000
        self.shares = 0
        self.done = False
        return self._get_state()

    def _get_state(self):
        window = self.data.iloc[self.current_step - self.seq_length:self.current_step]
        prices = window["close"].values
        sentiments = window["sentiment_score"].values
        state = np.concatenate([prices, sentiments])
        return state

    def step(self, action):
        current_price = self.data.iloc[self.current_step]["close"]
        reward = 0

        if action == 0:  # Buy
            if self.balance >= current_price:
                self.shares += 1
                self.balance -= current_price
                reward = self.data.iloc[self.current_step]["sentiment_score"]
        elif action == 1:  # Sell
            if self.shares > 0:
                self.shares -= 1
                self.balance += current_price
                reward = current_price - self.data.iloc[self.current_step - 1]["close"]
        # Action 2: Hold

        self.current_step += 1
        if self.current_step >= self.max_steps:
            self.done = True

        next_state = self._get_state()
        return next_state, reward, self.done

class SimplePolicy(nn.Module):
    def __init__(self, input_dim, hidden_dim=64):
        super(SimplePolicy, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, 3)  # Buy, Sell, Hold

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return torch.softmax(self.fc3(x), dim=-1)

def train_rlhf_strategy(stock_id, sentiment_data, episodes=100):
    env = StockTradingEnv(stock_id, sentiment_data)
    state_dim = env.seq_length * 2

    policy = SimplePolicy(state_dim)
    torch.save(policy.state_dict(), "initial_policy.pth")

    reward_model_path = "reward_model.pth"
    if not os.path.exists(reward_model_path):
        reward_model = SimplePolicy(state_dim)
        torch.save(reward_model.state_dict(), reward_model_path)

    with mlflow.start_run(run_name=f"RLHF_{stock_id}"):
        mlflow.log_param("episodes", episodes)
        mlflow.log_param("stock_id", stock_id)

        ray.init(ignore_reinit_error=True)
        train(
            pretrain="initial_policy.pth",
            reward_pretrain=reward_model_path,
            save_path=f"checkpoint/rlhf_{stock_id}",
            train_batch_size=128,
            micro_train_batch_size=16,
            rollout_batch_size=128,
            micro_rollout_batch_size=32,
            max_samples=10000,
            max_epochs=episodes,
            actor_learning_rate=5e-7,
            init_kl_coef=0.01,
            custom_env=env,
            use_wandb=False
        )

        trained_policy = SimplePolicy(state_dim)
        trained_policy.load_state_dict(torch.load(f"checkpoint/rlhf_{stock_id}/actor_final.pth"))
        mlflow.pytorch.log_model(trained_policy, "rlhf_model")
        logger.info(f"Completed RLHF training for {stock_id}")

    return trained_policy

def predict_action(model, env):
    state = env.reset()
    state_tensor = torch.FloatTensor(state).unsqueeze(0)
    with torch.no_grad():
        action_probs = model(state_tensor)
        action = torch.argmax(action_probs).item()
    return action

if __name__ == "__main__":
    stock_id = "0050"
    sentiment_data = [
        {"date": "2024-08-10", "sentiment": "positive"},
        {"date": "2024-08-11", "sentiment": "neutral"},
        {"date": "2024-08-12", "sentiment": "positive"}
    ]
    model = train_rlhf_strategy(stock_id, sentiment_data)
    env = StockTradingEnv(stock_id, sentiment_data)
    action = predict_action(model, env)
    logger.info(f"Predicted action for {stock_id}: {action}")