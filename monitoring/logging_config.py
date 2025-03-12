# monitoring/logging_config.py
import logging
from logstash_async.handler import AsynchronousLogstashHandler
from dotenv import load_dotenv
import os

def setup_logging():
    logger = logging.getLogger('stock_ai_project')
    logger.setLevel(logging.INFO)
    load_dotenv()

    logstash_handler = AsynchronousLogstashHandler(
        host=os.getenv("LOGSTASH_HOST", "localhost"),
        port=int(os.getenv("LOGSTASH_PORT", 5044)),
        database_path='logstash.db',
        transport='logstash_async.transport.TcpTransport'
    )
    logger.addHandler(logstash_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger