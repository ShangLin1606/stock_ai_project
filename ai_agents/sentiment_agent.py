import json
import pandas as pd
from pymilvus import connections, Collection, utility
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from redis import Redis
from monitoring.logging_config import setup_logging
from phi.assistant import Assistant
from phi.tools import Toolkit
from phi.model.xai import xAI

logger = setup_logging()
load_dotenv()

REDIS_HOST = "localhost"
redis_client = Redis(host=REDIS_HOST, port=6379, db=0)

MONGO_URI = f"mongodb://{os.getenv('MONGO_HOST', 'localhost')}:27017/"
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = "19530"
ES_CONFIG = {
    "hosts": ["http://localhost:9200"],
    "basic_auth": (os.getenv("ES_USERNAME", "elastic"), os.getenv("ES_PASSWORD", "P@ssw0rd"))
}
NEO4J_URI = f"neo4j://{os.getenv('NEO4J_HOST', 'localhost')}:7687"
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
XAI_API_KEY = os.getenv("XAI_API_KEY")

class SentimentToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="sentiment_tools")
        self.es_client = Elasticsearch(**ES_CONFIG)
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.register(self.search_mongodb)
        self.register(self.get_technical_indicator)
        self.register(self.query_graphrag)
        self.register(self.search_milvus)
        self.embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)

    def search_mongodb(self, stock_id: str, date: str) -> str:
        """從 MongoDB 搜索新聞"""
        try:
            from pymongo import MongoClient
            mongo_client = MongoClient(MONGO_URI)
            db = mongo_client["stock_news"]
            collection = db[f"news_{date[:4]}_{stock_id}"]
            news = list(collection.find({"date": {"$regex": date}}))
            mongo_client.close()
            return json.dumps(news if news else [])
        except Exception as e:
            logger.error(f"Error searching MongoDB: {str(e)}")
            return json.dumps([])

    def get_technical_indicator(self, stock_id: str, indicator: str) -> str:
        """獲取技術指標（假設已實現）"""
        # 這裡假設 TechnicalIndicators 已定義在 services 中
        from services.technical_indicators import TechnicalIndicators
        ti = TechnicalIndicators()
        result = ti.calculate(stock_id, indicator)
        return json.dumps({"indicator": indicator, "value": result})

    def query_graphrag(self, query: str) -> str:
        """查詢 Neo4j 知識圖譜"""
        try:
            with self.neo4j_driver.session() as session:
                result = session.run("MATCH (n) WHERE n.name =~ $query RETURN n", query=f".*{query}.*")
                nodes = [record["n"] for record in result]
            return json.dumps(nodes)
        except Exception as e:
            logger.error(f"Error querying Neo4j: {str(e)}")
            return json.dumps([])

    def search_milvus(self, stock_id: str, date: str, query: str, sentiment_filter: str = None) -> str:
        """從 Milvus 搜索相關新聞並根據情緒篩選"""
        try:
            collection_name = f"news_embeddings_{date[:4]}"
            if not utility.has_collection(collection_name):
                logger.warning(f"Milvus collection {collection_name} does not exist")
                return json.dumps([])

            collection = Collection(collection_name)
            collection.load()
            query_embedding = self.embedder.encode(query).tolist()
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=5,
                expr=f"stock_id == '{stock_id}'"
            )

            news_ids = [str(hit.id) for hit in results[0]]
            from pymongo import MongoClient
            mongo_client = MongoClient(MONGO_URI)
            db = mongo_client["stock_news"]
            news_items = db[f"news_{date[:4]}_{stock_id}"].find({"_id": {"$in": news_ids}})
            filtered_items = [
                item for item in news_items
                if not sentiment_filter or item["sentiment"] == sentiment_filter
            ]
            mongo_client.close()

            logger.info(f"Milvus found {len(filtered_items)} news items for {stock_id}")
            return json.dumps(filtered_items)
        except Exception as e:
            logger.error(f"Error searching Milvus: {str(e)}")
            return json.dumps([])

class SentimentAgent(Assistant):
    memory_key: str = "sentiment_memory"

    def __init__(self):
        toolkit = SentimentToolkit()
        super().__init__(
            name="SentimentAgent",
            model=xAI(id="grok-beta", api_key=XAI_API_KEY),
            description="Analyzes sentiment for stocks",
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

    def analyze(self, stock_id: str, date: str):
        """分析股票情緒"""
        try:
            news_json = self.tools[0].search_mongodb(stock_id=stock_id, date=date)
            news = json.loads(news_json)
            combined_text = " ".join([item["title"] + " " + item["content"] for item in news])

            # 使用 Milvus 搜索增強分析
            milvus_results_json = self.tools[0].search_milvus(stock_id=stock_id, date=date, query=combined_text, sentiment_filter="positive")
            milvus_news = json.loads(milvus_results_json)
            positive_news = " ".join([item["title"] + " " + item["content"] for item in milvus_news])

            prompt = (
                f"Analyze the sentiment of the following news for stock {stock_id} on {date}:\n"
                f"Combined News: {combined_text}\n"
                f"Positive News from Milvus: {positive_news}\n"
                f"Return a JSON string with 'stock_id', 'date', 'sentiment', and 'confidence'."
            )
            response = self.run(prompt)
            response_str = "".join([chunk for chunk in response if chunk is not None])
            result = json.loads(response_str)
            self.store_memory(result)
            return result
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return None

if __name__ == "__main__":
    agent = SentimentAgent()
    result = agent.analyze("0050", "2024-08-12")
    logger.info(f"Sentiment analysis result: {result}")