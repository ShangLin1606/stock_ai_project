from phi.assistant import Assistant
from phi.tools import Toolkit
from redis import Redis
from api.controllers.report_controller import ReportController
from dotenv import load_dotenv
import json
from monitoring.logging_config import setup_logging
import os
from phi.model.xai import xAI

logger = setup_logging()
load_dotenv()

REDIS_HOST = "localhost"
redis_client = Redis(host=REDIS_HOST, port=6379, db=0)
XAI_API_KEY = os.getenv("XAI_API_KEY")

class ReportToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="report_tools")
        self.report_controller = ReportController()
        self.register(self.generate_report)

    def generate_report(self, stock_id: str, start_date: str, end_date: str) -> str:
        report = self.report_controller.generate_report(stock_id, start_date, end_date)
        return json.dumps(report)

class ReportAgent(Assistant):
    memory_key: str = "report_memory"

    def __init__(self):
        toolkit = ReportToolkit()
        super().__init__(
            name="ReportAgent",
            model=xAI(id="grok-beta", api_key=XAI_API_KEY),
            description="Generates investment reports",
            tools=[toolkit],
            show_tool_calls=True
        )

    def store_memory(self, data):
        try:
            redis_client.set(self.memory_key, json.dumps(data))
            logger.info(f"Stored data in Redis for {self.name}: {data}")
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")

    def read_memory(self):
        try:
            data = redis_client.get(self.memory_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error reading memory: {str(e)}")
            return None

    def generate_report(self, stock_id: str, start_date: str, end_date: str):
        try:
            report_json = self.tools[0].generate_report(stock_id, start_date, end_date)
            report = json.loads(report_json)
            if not report:
                return None

            prompt = (
                f"Enhance the following investment report for stock {stock_id} from {start_date} to {end_date}:\n"
                f"{json.dumps(report)}\n"
                f"Add detailed insights and return a JSON string."
            )
            response = self.run(prompt)
            response_str = "".join([chunk for chunk in response if chunk is not None])
            enhanced_report = json.loads(response_str)
            self.store_memory(enhanced_report)
            return enhanced_report
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return None

if __name__ == "__main__":
    agent = ReportAgent()
    result = agent.generate_report("0050", "2024-08-01", "2024-08-12")
    logger.info(f"Report result: {result}")