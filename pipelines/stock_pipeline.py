from dagster import job, op, schedule, RunRequest
from scripts.update_daily_data import update_daily_stock_data
from src.infrastructure.crawler.stock_info_crawler import StockInfoCrawler

@op
def update_stock_info_op():
    crawler = StockInfoCrawler()
    crawler.update_stock_info()
    crawler.close()

@op
def update_stock_op():
    update_daily_stock_data()

@job
def stock_update_job():
    update_stock_info_op()
    update_stock_op()

@schedule(cron_schedule="0 18 * * *", job=stock_update_job, execution_timezone="Asia/Taipei")
def daily_stock_schedule():
    return RunRequest(run_key=None, run_config={})

if __name__ == "__main__":
    stock_update_job.execute_in_process()