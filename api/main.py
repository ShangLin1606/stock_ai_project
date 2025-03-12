from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware  # 導入 CORS 中間件
from api.controllers.stock_controller import StockController
from api.controllers.report_controller import ReportController
from api.controllers.strategy_controller import StrategyController
from api.controllers.news_controller import NewsController
from ai_agents.sentiment_agent import SentimentAgent
from ai_agents.strategy_agent import StrategyAgent
from ai_agents.report_agent import ReportAgent
from ai_agents.news_agent import NewsAgent
from dotenv import load_dotenv
import os
from redis import Redis
import json
import asyncio
from monitoring.logging_config import setup_logging

logger = setup_logging()
load_dotenv()

app = FastAPI(title="Stock API", description="API for stock data, trading, and news", version="1.0.0")

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],  # 允許前端來源
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有 HTTP 方法（如 GET、POST）
    allow_headers=["*"],  # 允許所有頭部
)

# 初始化控制器與 Agent
stock_controller = StockController()
report_controller = ReportController()
strategy_controller = StrategyController()
news_controller = NewsController()
sentiment_agent = SentimentAgent()
strategy_agent = StrategyAgent()
report_agent = ReportAgent()
news_agent = NewsAgent()

redis_client = Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0)
pubsub = redis_client.pubsub()
connected_clients = set()

# 以下為現有路由，保持不變
@app.get("/stocks/{stock_id}")
async def get_stock_data(stock_id: str, start_date: str = "2023-01-01", end_date: str = "2024-08-12"):
    cache_key = f"stock_{stock_id}_{start_date}_{end_date}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    try:
        data = stock_controller.get_stock_data(stock_id, start_date, end_date)
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for stock {stock_id}")
        redis_client.setex(cache_key, 3600, json.dumps(data))
        logger.info(f"Retrieved stock data for {stock_id}")
        return data
    except Exception as e:
        logger.error(f"Error retrieving stock data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ... 其餘路由保持不變 ...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)