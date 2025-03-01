FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04  # 假設存在，否則用 12.1 並升級

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y python3-pip python3-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install torch==2.3.0+cu121 torchvision==0.18.0+cu121 --index-url https://download.pytorch.org/whl/cu121
RUN pip install cython  # 確保 Cython 可用
RUN pip install -r requirements.txt

COPY . .
CMD ["python3", "scripts/test_env.py"]