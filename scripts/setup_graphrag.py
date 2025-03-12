from neo4j import GraphDatabase
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import time
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

NEO4J_URI = "bolt://localhost:7687"  # 容器外運行，改為 localhost
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

MONGO_HOST = "localhost"  # 容器外運行，改為 localhost
mongo_client = MongoClient(f"mongodb://{MONGO_HOST}:27017/")
mongo_db = mongo_client["stock_news"]

def wait_for_neo4j():
    max_attempts = 30
    for i in range(max_attempts):
        try:
            with neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info("Connected to Neo4j")
            return True
        except Exception as e:
            logger.warning(f"Waiting for Neo4j... Attempt {i+1}/{max_attempts}: {str(e)}")
            time.sleep(2)
    logger.error("Failed to connect to Neo4j after max attempts")
    return False

def setup_graphrag():
    if not wait_for_neo4j():
        return
    
    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        
        test_date = "2024-08-12"
        collections = mongo_db.list_collection_names()
        for coll_name in collections:
            if test_date in coll_name:
                stock_id = coll_name.split("_")[-1]
                news_items = mongo_db[coll_name].find()
                
                session.run(
                    "MERGE (s:Stock {stock_id: $stock_id})",
                    stock_id=stock_id
                )
                
                for item in news_items:
                    session.run(
                        """
                        MERGE (n:News {news_id: $news_id})
                        SET n.title = $title, n.content = $content, n.date = $date
                        WITH n
                        MATCH (s:Stock {stock_id: $stock_id})
                        MERGE (s)-[:HAS_NEWS]->(n)
                        """,
                        news_id=str(item["news_id"]),
                        title=item["title"],
                        content=item["content"],
                        date=item["publish_at"].split(" ")[0],
                        stock_id=stock_id
                    )
        logger.info("GraphRAG setup completed in Neo4j")

if __name__ == "__main__":
    setup_graphrag()