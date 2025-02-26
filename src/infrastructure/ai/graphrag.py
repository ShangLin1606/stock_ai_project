from src.infrastructure.database.mongo_handler import MongoHandler
from src.infrastructure.database.pgvector_handler import PgvectorHandler
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GraphRAG:
    def __init__(self):
        self.mongo = MongoHandler()
        self.pgvector = PgvectorHandler()

    def generate_knowledge_graph(self, query):
        logger.info(f"Generating knowledge graph for query: {query}")
        news_items = self.mongo.get_news_by_query(query)
        if not news_items:
            logger.warning(f"No news found for {query}, crawling now")
            from src.infrastructure.crawler.news_crawler import NewsCrawler
            crawler = NewsCrawler()
            crawler.crawl_and_store(query)
            news_items = self.mongo.get_news_by_query(query)

        # 簡單知識圖譜：僅列出新聞標題與關聯（未來可擴展至實體提取）
        graph = {"nodes": [], "edges": []}
        for item in news_items:
            graph["nodes"].append({"id": item["news_id"], "label": item["title"]})
            graph["edges"].append({"from": item["news_id"], "to": query, "relationship": "related_to"})
        
        logger.info(f"Generated simple knowledge graph with {len(news_items)} nodes")
        return graph

    def close(self):
        self.mongo.close()
        self.pgvector.close()

if __name__ == "__main__":
    graphrag = GraphRAG()
    graph = graphrag.generate_knowledge_graph("台積電")
    print(graph)
    graphrag.close()