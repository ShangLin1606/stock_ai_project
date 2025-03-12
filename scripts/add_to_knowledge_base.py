from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from sentence_transformers import SentenceTransformer
import pymongo
from dotenv import load_dotenv
import os
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

# MongoDB 配置
MONGO_HOST = "mongodb" if os.getenv("DOCKER_COMPOSE", "false").lower() == "true" else "localhost"
mongo_client = pymongo.MongoClient(f"mongodb://{MONGO_HOST}:27017/")
mongo_db = mongo_client["stock_news"]

# Milvus 配置
MILVUS_HOST = "localhost"
connections.connect(host=MILVUS_HOST, port="19530")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def fetch_all_news(date_str):
    """從 MongoDB 獲取指定日期的所有新聞"""
    try:
        collections = mongo_db.list_collection_names()
        news_data = []
        for collection_name in collections:
            if date_str in collection_name:
                collection = mongo_db[collection_name]
                news = collection.find()
                news_data.extend(news)
        logger.info(f"Fetched {len(news_data)} news items from MongoDB for date {date_str}")
        return news_data
    except Exception as e:
        logger.error(f"Error fetching news from MongoDB: {str(e)}")
        return []

def add_to_milvus(date_str, batch_size=1000):
    """將新聞數據分批嵌入 Milvus 知識庫"""
    news_data = fetch_all_news(date_str)
    if not news_data:
        logger.warning(f"No news data found for date {date_str}")
        return

    collection_name = f"news_embeddings_{date_str.replace('-', '')}"
    if utility.has_collection(collection_name):
        utility.drop_collection(collection_name)
        logger.info(f"Dropped existing Milvus collection {collection_name}")

    # 定義 Milvus 集合結構
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="stock_id", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="date", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
    ]
    schema = CollectionSchema(fields=fields, description="News embeddings")
    collection = Collection(collection_name, schema)
    collection.create_index("embedding", {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}})
    logger.info(f"Created Milvus collection {collection_name} with index")

    # 分批處理新聞數據
    total_records = len(news_data)
    for start in range(0, total_records, batch_size):
        end = min(start + batch_size, total_records)
        batch = news_data[start:end]
        entities = {"stock_id": [], "date": [], "embedding": []}

        # 處理批次中的每條新聞
        for i, news in enumerate(batch):
            stock_id = news["stock_id"]
            date = news["date"]
            text = f"{news['title']} {news['content']}"
            try:
                embedding = embedder.encode(text).tolist()
                entities["stock_id"].append(stock_id)
                entities["date"].append(date)
                entities["embedding"].append(embedding)
            except Exception as e:
                logger.error(f"Error embedding news {news['news_id']}: {str(e)}")
                continue

            # 每處理 100 條記錄一次進度
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {start + i + 1} of {total_records} news items in batch {start}-{end}")

        # 插入批次數據到 Milvus
        try:
            collection.insert([entities["stock_id"], entities["date"], entities["embedding"]])
            logger.info(f"Inserted batch {start}-{end} ({len(entities['stock_id'])} records) into Milvus")
        except Exception as e:
            logger.error(f"Error inserting batch {start}-{end} into Milvus: {str(e)}")

    # 完成所有批次後記錄
    collection.load()  # 確保數據可查詢
    logger.info(f"Completed adding {total_records} news records to Milvus collection {collection_name}")

def query_knowledge_base(stock_id, date):
    """從 Milvus 查詢新聞數據"""
    try:
        collection_name = f"news_embeddings_{date.replace('-', '')}"
        if not utility.has_collection(collection_name):
            logger.warning(f"Milvus collection {collection_name} does not exist")
            return None
        
        collection = Collection(collection_name)
        collection.load()
        query_text = f"News for stock {stock_id} on {date}"
        query_embedding = embedder.encode(query_text).tolist()
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=1,
            expr=f"stock_id == '{stock_id}'"
        )
        if results:
            hit = results[0][0]
            logger.info(f"Found news for {stock_id} on {date} with ID: {hit.id}")
            return hit.id
        return None
    except Exception as e:
        logger.error(f"Error querying Milvus: {str(e)}")
        return None

if __name__ == "__main__":
    date_str = "2025-03-05"  # 修改為您需要的日期
    add_to_milvus(date_str, batch_size=1000)
    stock_id = "0050"
    date = "2025-03-05"
    result = query_knowledge_base(stock_id, date)
    print(f"Query result for {stock_id} on {date}: {result}")