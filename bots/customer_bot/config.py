import os
from dotenv import load_dotenv

load_dotenv(override=False)

# TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 1C integration
ONEC_CUSTOMER_URL = os.getenv("ONEC_CUSTOMER_URL")
ONEC_API_KEY = os.getenv("INTEGRATION_API_KEY")

# Backend API (for /link command)
BACKEND_URL = os.getenv("BACKEND_URL", "http://app:8000")
