import os
# 禁用 GPU，強制使用 CPU
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import requests
from bs4 import BeautifulSoup
import pandas as pd
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
import time

# 設置編碼環境
os.environ["PYTHONIOENCODING"] = "utf-8"

class NewsCrawler:
    def __init__(self):
        # 使用輕量模型，減少記憶體使用
        self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.mongo_db = self.mongo_client["stock_news"]
        self.checkpoint_file = "crawler_checkpoint.json"
        self.max_pages = 10
        self.lock = threading.Lock()  # 保護模型訪問

    def load_checkpoint(self, stock_id):
        """載入檢查點，記錄最後爬取日期"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    checkpoints = json.load(f)
                    return checkpoints.get(stock_id, "2023-01-01")
            return "2023-01-01"
        except Exception as e:
            print(f"載入檢查點錯誤：{e}")
            return "2023-01-01"

    def save_checkpoint(self, stock_id, last_date):
        """保存檢查點，更新爬取進度"""
        try:
            checkpoints = {}
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    checkpoints = json.load(f)
            checkpoints[stock_id] = last_date
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoints, f)
        except Exception as e:
            print(f"保存檢查點錯誤：{e}")

    def crawl_cnyes_news_by_date(self, stock_id, date):
        """爬取鉅亨網指定日期新聞"""
        url = "https://news.cnyes.com/news/search"
        headers = {"User-Agent": "Mozilla/5.0"}
        date_str = date.strftime("%Y-%m-%d")
        params = {"q": stock_id, "start_date": date_str, "end_date": date_str, "page": 1}
        news_data = []
        page = 1

        while page <= self.max_pages:
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser", from_encoding="utf-8")
                articles = soup.select("article")

                if not articles:
                    print(f"{stock_id} 在 {date_str} 第 {page} 頁無文章")
                    break

                for article in articles:
                    title_elem = article.select_one("h3")
                    date_elem = article.select_one("time")
                    content_elem = article.select_one(".article__content")
                    if title_elem and date_elem and content_elem:
                        news_data.append({
                            "stock_id": stock_id,
                            "date": date_elem.text.strip(),
                            "title": title_elem.text.strip(),
                            "content": content_elem.text.strip()
                        })

                next_page = soup.select_one("a.next")
                if not next_page and page < self.max_pages:
                    print(f"{stock_id} 在 {date_str} 第 {page} 頁無下一頁")
                    break

                print(f"已爬取 {stock_id} 在 {date_str} 第 {page} 頁")
                page += 1
                params["page"] = page
                time.sleep(1)
            except Exception as e:
                print(f"爬取 {stock_id} 在 {date_str} 第 {page} 頁錯誤：{e}")
                break

        return news_data

    def generate_summary(self, news_item):
        """生成新聞摘要"""
        with self.lock:
            try:
                text = f"{news_item['title']} {news_item['content']}"[:512]  # 限制長度
                embedding = self.embedder.encode(text, convert_to_numpy=True)
                summary = text[:100] + "..." if len(text) > 100 else text
                return {"summary": summary}
            except Exception as e:
                print(f"生成摘要錯誤：{e}")
                return {"summary": ""}

    def store_to_mongodb(self, news_data, stock_id, date):
        """將新聞存入 MongoDB"""
        try:
            year = date[:4]
            collection = self.mongo_db[f"news_{year}_{stock_id}"]
            batch_size = 50
            for i in range(0, len(news_data), batch_size):
                batch = news_data[i:i + batch_size]
                for item in batch:
                    summary_data = self.generate_summary(item)
                    item.update(summary_data)
                    collection.update_one(
                        {"stock_id": item["stock_id"], "date": item["date"]},
                        {"$set": item},
                        upsert=True
                    )
                print(f"已存入 {stock_id} 在 {date} 的第 {i//batch_size + 1} 批次到 MongoDB")
        except Exception as e:
            print(f"存入 MongoDB 錯誤：{e}")

    def process_day(self, stock_id, date):
        """處理單天資料"""
        date_str = date.strftime("%Y-%m-%d")
        news_data = self.crawl_cnyes_news_by_date(stock_id, date)
        if news_data:
            self.store_to_mongodb(news_data, stock_id, date_str)
        self.save_checkpoint(stock_id, date_str)

    def run(self, stock_id, start_year=2023):
        """執行爬蟲"""
        start_date = pd.to_datetime(self.load_checkpoint(stock_id))
        end_date = datetime.today()
        days = [(start_date + timedelta(days=x)) for x in range((end_date - start_date).days + 1)]

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(self.process_day, stock_id, day) for day in days]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"線程錯誤：{e}")

if __name__ == "__main__":
    crawler = NewsCrawler()
    crawler.run("0050", start_year=2023)