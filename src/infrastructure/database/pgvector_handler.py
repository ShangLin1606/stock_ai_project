import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os
import numpy as np
from transformers import AutoTokenizer, AutoModel

load_dotenv()

class PgvectorHandler:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-chinese")
        self.model = AutoModel.from_pretrained("bert-base-chinese")
        self.create_table()

    def create_table(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS news_vectors (
                    id SERIAL PRIMARY KEY,
                    news_id TEXT UNIQUE,
                    vector VECTOR(768)
                );
            """)
            self.conn.commit()

    def get_embedding(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).detach().numpy().flatten()

    def insert_vectors(self, news_data):
        vectors = [(item['news_id'], self.get_embedding(item['content'])) for item in news_data]
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO news_vectors (news_id, vector)
                VALUES %s
                ON CONFLICT (news_id) DO NOTHING;
            """, [(news_id, np.array(vector).tolist()) for news_id, vector in vectors])
            self.conn.commit()

    def close(self):
        self.conn.close()