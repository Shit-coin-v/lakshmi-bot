import os

from dotenv import load_dotenv

load_dotenv(override=False)

COURIER_BOT_TOKEN = os.getenv("COURIER_BOT_TOKEN", "")
STORE_LOCATION = os.getenv("STORE_LOCATION", "село Намцы")
BACKEND_URL = os.getenv("BACKEND_URL", "http://app:8000")
INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")
