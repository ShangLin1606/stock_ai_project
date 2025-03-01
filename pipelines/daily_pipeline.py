from dagster import job, op, schedule
from scripts.data_fetcher import DataFetcher

@op
def update_daily_data_op():
    fetcher = DataFetcher()
    fetcher.fetch_twse_stock_info()
    fetcher.fetch_daily()
    fetcher.close()

@job
def daily_update_job():
    update_daily_data_op()

@schedule(cron_schedule="0 18 * * *", job=daily_update_job, execution_timezone="Asia/Taipei")
def daily_stock_schedule():
    return {}