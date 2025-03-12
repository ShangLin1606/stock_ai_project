from dagster import asset
import yfinance as yf
import requests
import pandas as pd
import psycopg2
import asyncio
import aiohttp
import pymongo
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
import json
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

# PostgreSQL 配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

# MongoDB 配置
MONGO_HOST = "mongodb" if os.getenv("DOCKER_COMPOSE", "false").lower() == "true" else "localhost"
mongo_client = pymongo.MongoClient(f"mongodb://{MONGO_HOST}:27017/")
mongo_db = mongo_client["stock_news"]

# Elasticsearch 配置
es_client = Elasticsearch(
    [f"http://{os.getenv('ES_HOST', 'localhost')}:{os.getenv('ES_PORT')}"],
    basic_auth=(os.getenv('ES_USERNAME', 'elastic'), os.getenv('ES_PASSWORD'))
)

# Milvus 配置（移除模組級連線）
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

@asset
def stock_list():
    """更新股票列表資產"""
    conn = None
    cursor = None
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        logger.info("Fetching stock list from TWSE API")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data)[['Code', 'Name']]
        df.columns = ['stock_id', 'stock_name']
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("TRUNCATE TABLE stocks;")
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO stocks (stock_id, stock_name)
                VALUES (%s, %s)
                ON CONFLICT (stock_id) DO UPDATE SET stock_name = EXCLUDED.stock_name;
            """, (row['stock_id'], row['stock_name']))
        
        conn.commit()
        logger.info(f"Updated stock list with {len(df)} entries")
        return list(df.itertuples(index=False, name=None))
    
    except Exception as e:
        logger.error(f"Error updating stock list: {str(e)}")
        return []
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@asset
def daily_prices(stock_list):
    """更新每日股價資產，依賴 stock_list"""
    conn = None
    cursor = None
    try:
        yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        logger.info(f"Fetching daily prices for {yesterday}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        for stock_id, _ in stock_list:
            ticker = f"{stock_id}.TW" if stock_id != "大盤" else "^TWII"
            logger.info(f"Fetching daily data for {ticker}")
            
            df = yf.download(ticker, start=yesterday, end=yesterday, progress=False)
            if df.empty:
                logger.warning(f"No data found for {ticker} on {yesterday}")
                continue
            
            df['stock_id'] = stock_id
            df.columns = ['open', 'high', 'low', 'close', 'volume', 'stock_id'] if 'Adj Close' not in df.columns else ['open', 'high', 'low', 'close', 'adj_close', 'volume', 'stock_id']
            
            for index, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO daily_prices (date, stock_id, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, stock_id) DO NOTHING;
                """, (index.date(), row['stock_id'], row['open'], row['high'], row['low'], row['close'], int(row['volume'])))
        
        conn.commit()
        logger.info("Updated daily prices")
        return None
    
    except Exception as e:
        logger.error(f"Error updating daily prices: {str(e)}")
        return None
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def fetch_page(session, stock_name, stock_id, page):
    """非同步爬取單頁新聞"""
    url = f"https://ess.api.cnyes.com/ess/api/v1/news/keyword?q={stock_name}&page={page}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            response.raise_for_status()
            data = await response.json()
            return data['data']['items']
    except Exception as e:
        logger.error(f"Error fetching page {page} for {stock_name} (ID: {stock_id}): {str(e)}")
        return []

async def crawl_and_embed_news(stock_id, stock_name, date_str):
    """爬取新聞並嵌入 Milvus"""
    collection = mongo_db[f"news_{date_str}_{stock_id}"]
    collection_name = f"news_embeddings_{date_str.replace('-', '')}"
    
    # 連接到 Milvus
    try:
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT, timeout=10)
    except Exception as e:
        logger.error(f"Failed to connect to Milvus: {str(e)}")
        return
    
    # 若 Milvus 集合已存在，先清空
    if utility.has_collection(collection_name):
        utility.drop_collection(collection_name)
    
    # 初始化 Milvus 集合
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="stock_id", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="date", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
    ]
    schema = CollectionSchema(fields=fields, description="News embeddings")
    milvus_collection = Collection(collection_name, schema)
    milvus_collection.create_index("embedding", {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}})

    async with aiohttp.ClientSession() as session:
        page = 1
        processed_docs = set()
        while True:
            logger.info(f"Crawling news for {stock_name} (ID: {stock_id}), page {page}")
            news_data = await fetch_page(session, stock_name, stock_id, page)
            
            if not news_data:
                logger.info(f"No more news for {stock_name} (ID: {stock_id}) after page {page}")
                break
            
            entities = {"stock_id": [], "date": [], "embedding": []}
            for item in news_data:
                news_id = item["newsId"]
                if news_id in processed_docs:
                    continue
                
                news_doc = {
                    "stock_id": stock_id,
                    "stock_name": stock_name,
                    "news_id": news_id,
                    "title": item["title"],
                    "publish_at": datetime.fromtimestamp(item["publishAt"]).strftime('%Y-%m-%d %H:%M:%S'),
                    "content": item.get("summary", ""),
                    "date": date_str
                }
                collection.insert_one(news_doc)
                
                es_doc = news_doc.copy()
                es_client.index(index=f"stock_news_{date_str}", id=news_id, body=es_doc)
                
                text = f"{news_doc['title']} {news_doc['content']}"
                embedding = embedder.encode(text).tolist()
                entities["stock_id"].append(stock_id)
                entities["date"].append(date_str)
                entities["embedding"].append(embedding)
                processed_docs.add(news_id)
            
            milvus_collection.insert([entities["stock_id"], entities["date"], entities["embedding"]])
            logger.info(f"Stored and embedded {len(news_data)} news items for {stock_name} (ID: {stock_id}), page {page}")
            page += 1
            await asyncio.sleep(0.5)

@asset
def news_data(stock_list):
    """依賴 stock_list 資產，爬取並嵌入新聞數據，每日更新"""
    date_str = datetime.today().strftime('%Y-%m-%d')
    stocks = [(stock_id, stock_name) for stock_id, stock_name in stock_list]
    
    async def run_all():
        tasks = [crawl_and_embed_news(stock_id, stock_name, date_str) for stock_id, stock_name in stocks]
        await asyncio.gather(*tasks)
    
    asyncio.run(run_all())
    logger.info("Completed news crawling and embedding for all stocks")
    return None

def fetch_all_news(date_str):
    """從 MongoDB 獲取指定日期的所有新聞（備用函數）"""
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

def query_knowledge_base(stock_id, date):
    """從 Milvus 查詢新聞數據（測試用）"""
    try:
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT, timeout=10)
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
        if results and len(results[0]) > 0:
            hit = results[0][0]
            logger.info(f"Found news for {stock_id} on {date} with ID: {hit.id}")
            return hit.id
        logger.info(f"No matching news found in Milvus for {stock_id} on {date}")
        return None
    except Exception as e:
        logger.error(f"Error querying Milvus: {str(e)}")
        return None

if __name__ == "__main__":
    # 測試執行
    stocks = stock_list()
    daily_prices(stocks)
    news_data(stocks)
    date_str = datetime.today().strftime('%Y-%m-%d')
    stock_id = "0050"
    result = query_knowledge_base(stock_id, date_str)
    print(f"Query result for {stock_id} on {date_str}: {result}")