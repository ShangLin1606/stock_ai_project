FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.presentation.api.views.api_views:app", "--host", "0.0.0.0", "--port", "8000"]
