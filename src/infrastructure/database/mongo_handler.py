from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

class MongoHandler:
    def __init__(self):
        self.client = MongoClient(
            host=os.getenv("MONGO_HOST"),
            port=int(os.getenv("MONGO_PORT"))
        )
        self.db = self.client[os.getenv("MONGO_DB")]
        self.collection = self.db['news']

    def insert_news(self, news_data):
        self.collection.insert_many(news_data)
    
    def clear_daily_news(self):
        self.collection.delete_many({})
    
    def get_news_by_query(self, query):
        return list(self.collection.find({"$text": {"$search": query}}))

    def close(self):
        self.client.close()