from phi.assistant import Assistant
from phi.model.xai import xAI
from redis import Redis
import time
from dotenv import load_dotenv
import os
import json
import torch
from models.transformer import train_transformer, predict_price
from tools.fetch_historical import fetch_historical
from services.technical_indicators import TechnicalIndicators
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

REDIS_HOST = "localhost"
redis_client = Redis(host=REDIS_HOST, port=6379, db=0)

XAI_API_KEY = os.getenv("XAI_API_KEY")
if not XAI_API_KEY:
    raise ValueError("XAI_API_KEY environment variable is not set. Please set it to use Grok.")

class PredictionToolkit():
    def __init__(self):
        super().__init__(name="prediction_tools")
        self.register(self.get_technical_indicator)
        self.register(self.fetch_historical_data)
        self.model_cache = {}  # 緩存訓練好的模型和 scaler

    def get_technical_indicator(self, stock_id: str, indicator: str) -> float:
        try:
            tech_indicators = TechnicalIndicators()
            result = tech_indicators.calculate(stock_id, indicator)
            return result
        except Exception as e:
            logger.error(f"Error calculating technical indicator: {str(e)}")
            return 0.0

    def fetch_historical_data(self, stock_id: str, period: str = "1y") -> str:
        try:
            df = fetch_historical(stock_id, period)
            if df is None:
                return json.dumps([])
            return df.to_json()
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return json.dumps([])

class PredictionAgent(Assistant):
    memory_key: str = "prediction_memory"

    def __init__(self):
        toolkit = PredictionToolkit()
        super().__init__(
            name="PredictionAgent",
            model=xAI(id="grok-beta", api_key=XAI_API_KEY),
            description="Predicts stock prices",
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

    def predict(self, stock_id: str, sentiment: str):
        """預測股價，使用 Transformer 或 LLM"""
        try:
            # 使用 Transformer 預測
            if stock_id not in self.tools[0].model_cache:
                model, scaler = train_transformer(stock_id)
                if model and scaler:
                    self.tools[0].model_cache[stock_id] = (model, scaler)
                else:
                    logger.warning(f"Failed to train Transformer for {stock_id}, falling back to LLM")
                    return self.predict_with_llm(stock_id, sentiment)
            
            model, scaler = self.tools[0].model_cache[stock_id]
            pred_price = predict_price(model, scaler, stock_id)
            if pred_price is not None:
                result = {"stock_id": stock_id, "predicted_price": pred_price}
                self.store_memory(result)
                return result

            # 若 Transformer 失敗，後備使用 LLM
            return self.predict_with_llm(stock_id, sentiment)
        except Exception as e:
            logger.error(f"Error predicting price with Transformer: {str(e)}")
            return self.predict_with_llm(stock_id, sentiment)

    def predict_with_llm(self, stock_id: str, sentiment: str):
        """使用 LLM 預測股價變化"""
        prompt = (
            f"Based on a sentiment of '{sentiment}' for stock ID {stock_id}, predict the next day's stock price change "
            f"as a percentage (e.g., '+5%' or '-3%'). Return ONLY a JSON string with 'stock_id' and 'predicted_change'."
        )
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response_generator = self.run(prompt)
                response = "".join([chunk for chunk in response_generator if chunk is not None])
                if response.strip() == "":
                    logger.warning(f"LLM attempt {attempt + 1}/{max_attempts} returned empty response")
                    time.sleep(2)
                    continue
                logger.info(f"Raw LLM response: {response}")
                result = json.loads(response)
                self.store_memory(result)
                return result
            except Exception as e:
                logger.error(f"LLM attempt {attempt + 1}/{max_attempts} error: {str(e)}")
                time.sleep(2)
        
        logger.warning(f"No valid LLM response after {max_attempts} attempts, using default change '0%'")
        result = {"stock_id": stock_id, "predicted_change": "0%"}
        self.store_memory(result)
        return result

if __name__ == "__main__":
    agent = PredictionAgent()
    result = agent.predict("0050", "positive")
    logger.info(f"Prediction result: {result}")