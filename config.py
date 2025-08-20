# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file if running locally
load_dotenv()

class Config:
    # Pocket Option credentials
    PO_EMAIL = os.getenv("PO_EMAIL")
    PO_PASSWORD = os.getenv("PO_PASSWORD")

    # Pocket Option API/WebSocket base URL
    # (WebSocket: "wss://ws.pocketoption.com/quotes-service-v1/ws" OR REST endpoint if you’re polling)
    PO_API_BASE = "wss://ws.pocketoption.com/quotes-service-v1/ws"

    # Telegram bot (optional: remove if not needed)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Default trading symbols (Pocket Option currency pairs)
    SYMBOLS = [
        "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc",
        "USDCAD_otc", "USDCHF_otc", "EURGBP_otc", "EURJPY_otc",
        "GBPJPY_otc", "AUDJPY_otc"
    ]

    # Timeframes for scanning
    TIMEFRAMES = ["1m", "2m", "3m", "5m"]

    # App mode
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
