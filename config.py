# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file if running locally
load_dotenv()

class Config:
    # Pocket Option credentials
    PO_EMAIL = os.getenv("PO_EMAIL")
    PO_PASSWORD = os.getenv("PO_PASSWORD")

    # Telegram bot (optional: remove if not needed)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # App mode
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
