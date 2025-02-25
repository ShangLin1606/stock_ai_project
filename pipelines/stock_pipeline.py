from dagster import job, op, schedule, RunRequest
from scripts.update_daily_data import update_daily_stock_data

@op
def update_stock_op():
    update_daily_stock_data()

@job
def stock_update_job():
    update_stock_op()

@schedule(cron_schedule="0 15 * * *", job=stock_update_job, execution_timezone="Asia/Taipei")
def daily_stock_schedule():
    return RunRequest(run_key=None, run_config={})

# 啟動 Dagster UI（手動運行時使用）
if __name__ == "__main__":
    stock_update_job.execute_in_process()