from phi.assistant import Assistant
from phi.tools import Toolkit
from redis import Redis
from api.controllers.news_controller import NewsController
from dotenv import load_dotenv
import json
from monitoring.logging_config import setup_logging
from phi.model.xai import xAI
import os

logger = setup_logging()
load_dotenv()

REDIS_HOST = "localhost"
redis_client = Redis(host=REDIS_HOST, port=6379, db=0)
XAI_API_KEY = os.getenv("XAI_API_KEY")

class NewsToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="news_tools")
        self.news_controller = NewsController()
        self.register(self.search_news)

    def search_news(self, stock_id: str, query: str, date: str = None, sentiment: str = None, tags: str = None) -> str:
        tags_list = tags.split(",") if tags else None
        results = self.news_controller.search_news(stock_id, query, date, sentiment, tags_list)
        return json.dumps(results)

class NewsAgent(Assistant):
    memory_key: str = "news_memory"

    def __init__(self):
        toolkit = NewsToolkit()
        super().__init__(
            name="NewsAgent",
            model=xAI(id="grok-beta", api_key=XAI_API_KEY),
            description="Handles news search and processing",
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

    def search_news(self, stock_id: str, query: str, date: str = None, sentiment: str = None, tags: list = None):
        try:
            news_json = self.tools[0].search_news(stock_id, query, date, sentiment, ",".join(tags) if tags else None)
            news_items = json.loads(news_json)
            if not news_items:
                return []

            prompt = (
                f"Analyze and summarize the following news items for stock {stock_id}:\n"
                f"{json.dumps(news_items)}\n"
                f"Return a JSON string with 'stock_id', 'summary', and 'key_insights'."
            )
            response = self.run(prompt)
            response_str = "".join([chunk for chunk in response if chunk is not None])
            summary = json.loads(response_str)
            self.store_memory(summary)
            return summary
        except Exception as e:
            logger.error(f"Error searching news: {str(e)}")
            return []

if __name__ == "__main__":
    agent = NewsAgent()
    result = agent.search_news("0050", "市場動態", "2024-08-12", "positive", ["市場", "ETF"])
    logger.info(f"News search result: {result}")