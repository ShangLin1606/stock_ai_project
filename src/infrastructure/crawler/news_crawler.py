import requests
from bs4 import BeautifulSoup
import logging
from src.infrastructure.database.mongo_handler import MongoHandler
from src.infrastructure.database.pgvector_handler import PgvectorHandler
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsCrawler:
    def __init__(self):
        self.mongo = MongoHandler()
        self.pgvector = PgvectorHandler()

    def fetch_news(self, query, limit=5):
        url = f'https://ess.api.cnyes.com/ess/api/v1/news/keyword?q={query}&limit={limit}&page=1'
        try:
            response = requests.get(url)
            json_data = response.json()
            items = json_data['data']['items']
            news_data = []
            for item in items:
                news_id = str(item["newsId"])
                title = item["title"]
                publish_at = datetime.utcfromtimestamp(item["publishAt"]).strftime('%Y-%m-%d')
                content_url = f'https://news.cnyes.com/news/id/{news_id}'
                content_response = requests.get(content_url)
                soup = BeautifulSoup(content_response.content, 'html.parser')
                p_elements = soup.find_all('p')[4:]
                content = ''.join(p.get_text() for p in p_elements)
                news_data.append({
                    "news_id": news_id,
                    "title": title,
                    "publish_at": publish_at,
                    "content": content,
                    "query": query
                })
            return news_data
        except Exception as e:
            logger.error(f"Error fetching news for {query}: {str(e)}")
            return []

    def crawl_and_store(self, query):
        logger.info(f"Crawling news for query: {query}")
        news_data = self.fetch_news(query)
        if news_data:
            self.mongo.insert_news(news_data)
            self.pgvector.insert_vectors(news_data)
            logger.info(f"Stored {len(news_data)} news items for {query}")
        else:
            logger.warning(f"No news fetched for {query}")

    def close(self):
        self.mongo.close()
        self.pgvector.close()

if __name__ == "__main__":
    crawler = NewsCrawler()
    crawler.crawl_and_store("台積電")
    crawler.close()