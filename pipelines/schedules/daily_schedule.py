from dagster import ScheduleDefinition, define_asset_job
from pipelines.assets.assets import stock_list, daily_prices, news_data

# 定義資產作業，包括所有資產
daily_update_job = define_asset_job(
    name="daily_update_job",
    selection=[stock_list, daily_prices, news_data]  # 使用資產定義
)

# 每日下午 2 點排程（UTC 06:00 = 台灣時間 14:00）
daily_schedule = ScheduleDefinition(
    job=daily_update_job,
    cron_schedule="0 6 * * *",
    execution_timezone="UTC"
)