import os

from dotenv import load_dotenv

load_dotenv(override=False)

COURIER_BOT_TOKEN = os.getenv("COURIER_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://app:8000")
INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")

# Whitelist Telegram IDs для курьеров
_raw_ids = os.getenv("COURIER_ALLOWED_TG_IDS", "")
COURIER_ALLOWED_TG_IDS: set[int] = set()
if _raw_ids:
    for part in _raw_ids.split(","):
        part = part.strip()
        if part.isdigit():
            COURIER_ALLOWED_TG_IDS.add(int(part))
