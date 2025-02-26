import requests
import pandas as pd
from src.infrastructure.database.pg_handler import PostgresHandler
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinancialCrawler:
    def __init__(self):
        self.pg = PostgresHandler()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_financial_data(self, stock_id, year, retries=3, delay=5):
        url = f"https://mops.twse.com.tw/mops/web/ajax_t164sb03?encodeURIComponent=1&step=1&firstin=1&off=1&TYPEK=all&year={year}&season=04&co_id={stock_id}"
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                html = response.text
                dfs = pd.read_html(html)
                if not dfs:
                    raise ValueError("No tables found in response")
                # 假設財報數據在第一個表格中，需根據實際結構調整
                df = dfs[0]
                # 模擬簡單解析，實際需根據財報表格結構提取
                financial_data = pd.DataFrame({
                    'year': [year],
                    'quarter': [4],  # 假設抓取第四季全年數據
                    'revenue': [float(df.iloc[0, 1]) if len(df) > 0 else 0],  # 營收（假設）
                    'eps': [float(df.iloc[1, 1]) if len(df) > 1 else 0]      # EPS（假設）
                })
                logger.info(f"Fetched financial data for {stock_id} year {year}")
                return financial_data
            except (requests.RequestException, ValueError) as e:
                logger.error(f"Attempt {attempt + 1} failed for {stock_id} year {year}: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    logger.warning(f"Failed to fetch financial data for {stock_id} year {year}")
                    return pd.DataFrame()

    def crawl_financial_reports(self, years=[2024]):
        stocks = self.pg.get_all_stocks_from_name_df()
        for stock_id in stocks[:10]:  # 先測試 10 檔，避免過載
            for year in years:
                df = self.fetch_financial_data(stock_id, year)
                if not df.empty:
                    self.pg.insert_financial_report(stock_id, df)
                time.sleep(1)  # 避免過快請求

    def close(self):
        self.pg.close()

if __name__ == "__main__":
    crawler = FinancialCrawler()
    try:
        crawler.crawl_financial_reports()
    except Exception as e:
        logger.error(f"Crawl failed: {str(e)}")
    finally:
        crawler.close()