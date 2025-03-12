from pymilvus import connections, Collection, utility
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import pandas as pd
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

MONGO_URI = f"mongodb://{os.getenv('MONGO_HOST', 'localhost')}:27017/"
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = "19530"

class NewsController:
    def __init__(self):
        self.embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)

    def search_news(self, stock_id: str, query: str, date: str = None, sentiment: str = None, tags: list = None):
        """從 Milvus 和 MongoDB 搜索新聞"""
        try:
            year = date[:4] if date else str(pd.Timestamp.now().year)
            collection_name = f"news_embeddings_{year}"
            if not utility.has_collection(collection_name):
                logger.warning(f"Milvus collection {collection_name} does not exist")
                return []

            collection = Collection(collection_name)
            collection.load()
            query_embedding = self.embedder.encode(query).tolist()
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=10,
                expr=f"stock_id == '{stock_id}'"
            )

            news_ids = [str(hit.id) for hit in results[0]]
            mongo_client = MongoClient(MONGO_URI)
            db = mongo_client["stock_news"]
            collection = db[f"news_{year}_{stock_id}"]
            news_items = list(collection.find({"_id": {"$in": news_ids}}))

            filtered_items = [
                item for item in news_items
                if (not sentiment or item["sentiment"] == sentiment) and
                   (not tags or any(tag in item["tags"] for tag in tags))
            ]
            mongo_client.close()

            logger.info(f"Found {len(filtered_items)} news items for {stock_id}")
            return filtered_items
        except Exception as e:
            logger.error(f"Error searching news: {str(e)}")
            return []