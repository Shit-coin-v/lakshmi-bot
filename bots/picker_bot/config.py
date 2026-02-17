import os

from dotenv import load_dotenv

load_dotenv(override=False)

PICKER_BOT_TOKEN = os.getenv("PICKER_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://app:8000")
INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")

# Whitelist Telegram IDs для сборщиков
_raw_ids = os.getenv("PICKER_ALLOWED_TG_IDS", "")
PICKER_ALLOWED_TG_IDS: set[int] = set()
if _raw_ids:
    for part in _raw_ids.split(","):
        part = part.strip()
        if part.isdigit():
            PICKER_ALLOWED_TG_IDS.add(int(part))
