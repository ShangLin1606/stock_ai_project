import pytest
from src.infrastructure.crawler.news_crawler import NewsCrawler
from src.infrastructure.database.mongo_handler import MongoHandler
from src.infrastructure.database.pgvector_handler import PgvectorHandler

@pytest.fixture
def crawler():
    c = NewsCrawler()
    yield c
    c.close()

@pytest.fixture
def mongo():
    m = MongoHandler()
    m.clear_daily_news()  # 清空測試數據
    yield m
    m.close()

@pytest.fixture
def pgvector():
    p = PgvectorHandler()
    with p.conn.cursor() as cur:
        cur.execute("TRUNCATE news_vectors;")
        p.conn.commit()
    yield p
    p.close()

def test_crawl_and_store(crawler, mongo, pgvector):
    crawler.crawl_and_store("台積電")
    news = mongo.get_news_by_query("台積電")
    assert len(news) > 0
    with pgvector.conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM news_vectors;")
        count = cur.fetchone()[0]
    assert count > 0