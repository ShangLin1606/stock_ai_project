# 基礎映像
FROM python:3.10 AS builder

WORKDIR /opt/dagster/app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製並安裝 Python 依賴
COPY dagster_requirements.txt .
RUN pip install --no-cache-dir -r dagster_requirements.txt

# 最終映像
FROM python:3.10

WORKDIR /opt/dagster/app

# 僅複製必要的系統依賴
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# 從 builder 複製已安裝的依賴
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=builder /usr/local/bin/dagster* /usr/local/bin/

# 複製專案檔案
COPY . .

ENV PYTHONPATH=/opt/dagster/app

CMD ["dagster", "dev"]