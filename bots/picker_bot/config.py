import os

from dotenv import load_dotenv

load_dotenv(override=False)

PICKER_BOT_TOKEN = os.getenv("PICKER_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://app:8000")
INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")
