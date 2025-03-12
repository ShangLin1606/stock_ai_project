import psycopg2
import redis
from pymongo import MongoClient
from pymilvus import connections
import os 
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 資料庫配置字典
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

#測試PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
print("PostgreSQL 連接成功")
conn.close()

#測試Redis
r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"))
r.set("test_key", "test_value")
print(f"Redis 連接成功，讀取值: {r.get("test_key").decode("utf-8")}")

#測試MongoDB
client = MongoClient(os.getenv("MONGO_HOST"), os.getenv("MONGO_PORT"))
db = client["stock_news"]
print("MongoDB 連接成功")

#測試Milvus
connections.connect(host=os.getenv("MILVUS_HOST"), port=os.getenv("MILVUS_PORT"))
print("Milvus 連接成功")
