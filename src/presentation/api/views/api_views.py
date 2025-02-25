from fastapi import FastAPI
from src.infrastructure.database.pg_handler import PostgresHandler
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

@app.get("/stocks/{stock_id}/latest")
async def get_latest_stock_data(stock_id: str):
    pg = PostgresHandler()
    try:
        with pg.conn.cursor() as cur:
            cur.execute("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM stock_prices
                WHERE stock_id = %s
                ORDER BY date DESC
                LIMIT 1;
            """, (stock_id,))
            result = cur.fetchone()
            if result:
                return {
                    "stock_id": stock_id,
                    "date": result[0].strftime('%Y-%m-%d'),
                    "open": float(result[1]),
                    "high": float(result[2]),
                    "low": float(result[3]),
                    "close": float(result[4]),
                    "volume": int(result[5])
                }
            return {"error": f"No data found for {stock_id}"}
    finally:
        pg.close()

# 啟動 FastAPI（測試用）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)