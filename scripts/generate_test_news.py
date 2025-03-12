from pymongo import MongoClient
from elasticsearch import Elasticsearch
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
import json
import time
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

MONGO_HOST = "localhost"
mongo_client = MongoClient(f"mongodb://{MONGO_HOST}:27017/")
mongo_db = mongo_client["stock_news"]

es_client = Elasticsearch(
    ["http://localhost:9200"],
    basic_auth=(os.getenv('ES_USERNAME'), os.getenv('ES_PASSWORD'))
)

MILVUS_HOST = "localhost"
connections.connect(host=MILVUS_HOST, port="19530")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def wait_for_milvus():
    max_attempts = 30
    for i in range(max_attempts):
        try:
            connections.connect(host=MILVUS_HOST, port="19530")
            logger.info("Connected to Milvus")
            return True
        except Exception as e:
            logger.warning(f"Waiting for Milvus... Attempt {i+1}/{max_attempts}: {str(e)}")
            time.sleep(2)
    logger.error("Failed to connect to Milvus after max attempts")
    return False

def generate_test_news():
    if not wait_for_milvus():
        return
    
    test_date = "2024-08-12"
    milvus_date_str = "20240812"  # 移除連字符以符合 Milvus 要求
    test_stocks = [
        {"stock_id": "0050", "stock_name": "元大台灣50"},
        {"stock_id": "2330", "stock_name": "台積電"}
    ]
    
    test_news = [
        {
            "stock_id": "0050",
            "stock_name": "元大台灣50",
            "news_id": 1,
            "title": "元大台灣50 上漲 2%，市場樂觀",
            "publish_at": "2024-08-12 10:00:00",
            "content": "元大台灣50 今日表現強勁，帶動大盤上漲，投資人信心增強。"
        },
        {
            "stock_id": "0050",
            "stock_name": "元大台灣50",
            "news_id": 2,
            "title": "元大台灣50 盤中震盪",
            "publish_at": "2024-08-12 14:00:00",
            "content": "元大台灣50 下午盤中出現波動，但整體趨勢穩定。"
        },
        {
            "stock_id": "2330",
            "stock_name": "台積電",
            "news_id": 3,
            "title": "台積電 新廠開工，預計提升產能",
            "publish_at": "2024-08-12 09:00:00",
            "content": "台積電宣布新廠計劃，市場預期將強化其全球地位。"
        }
    ]

    # 清空現有數據
    for stock in test_stocks:
        mongo_db[f"news_{test_date}_{stock['stock_id']}"].drop()

    # 儲存到 MongoDB 和 Elasticsearch
    for news in test_news:
        stock_id = news["stock_id"]
        collection = mongo_db[f"news_{test_date}_{stock_id}"]
        inserted_doc = collection.insert_one(news)
        news_without_id = news.copy()
        del news_without_id["_id"]  # 移除 MongoDB 自動生成的 _id
        es_client.index(index=f"stock_news_{test_date}", id=news["news_id"], body=news_without_id)

    # 嵌入 Milvus
    milvus_collection_name = f"news_embeddings_{milvus_date_str}"  # 使用合法名稱
    if utility.has_collection(milvus_collection_name):
        utility.drop_collection(milvus_collection_name)
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="stock_id", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="news_id", dtype=DataType.INT64),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
    ]
    schema = CollectionSchema(fields=fields, description="News embeddings")
    milvus_collection = Collection(milvus_collection_name, schema)
    milvus_collection.create_index("embedding", {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}})

    entities = {"stock_id": [], "news_id": [], "embedding": []}
    for news in test_news:
        embedding = embedder.encode(news["content"]).tolist()
        entities["stock_id"].append(news["stock_id"])
        entities["news_id"].append(news["news_id"])
        entities["embedding"].append(embedding)
    
    milvus_collection.insert([entities["stock_id"], entities["news_id"], entities["embedding"]])
    logger.info(f"Generated and stored {len(test_news)} test news items in MongoDB, Elasticsearch, and Milvus")

if __name__ == "__main__":
    generate_test_news()