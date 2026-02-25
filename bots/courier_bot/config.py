import os

from dotenv import load_dotenv

load_dotenv(override=False)

COURIER_BOT_TOKEN = os.getenv("COURIER_BOT_TOKEN", "")
STORE_LOCATION = os.getenv("STORE_LOCATION", "село Намцы")
BACKEND_URL = os.getenv("BACKEND_URL", "http://app:8000")
INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")

# Singleton BackendClient — one per bot process
from shared.clients.backend_client import BackendClient  # noqa: E402
backend = BackendClient(BACKEND_URL, INTEGRATION_API_KEY)
