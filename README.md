# Stock AI Project

一個基於 AI 的股票分析平台，提供股價查詢、情緒分析、交易策略建議與新聞搜索功能。

## 功能
- **股價查詢**：查看股票歷史價格與最新數據。
- **投資報告**：生成股票期間分析報告。
- **交易策略**：提供基於多模型的交易建議。
- **新聞搜索**：搜索與分析股票相關新聞。
- **可視化**：使用 Kibana 展示用戶行為，Grafana 監控系統性能。

## 技術棧
- **後端**：FastAPI (Python)
- **前端**：React (TypeScript)
- **數據庫**：PostgreSQL, MongoDB, Milvus, Neo4j
- **搜尋與監控**：Elasticsearch, Kibana, Prometheus, Grafana
- **容器化**：Docker, Docker Compose

## 環境要求
- Docker & Docker Compose
- Git
- Node.js (本地開發用)
- Python 3.9+ (本地開發用)

## 安裝與部署

### 1. Clone 倉庫
```bash
git clone git@ShangLin1606/stock_ai_project.git
cd stock_ai_project