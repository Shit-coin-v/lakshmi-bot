import os
from dotenv import load_dotenv

load_dotenv()

# TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 1C integration
ONEC_CUSTOMER_URL = os.getenv("ONEC_CUSTOMER_URL")
ONEC_API_KEY = os.getenv("INTEGRATION_API_KEY")
