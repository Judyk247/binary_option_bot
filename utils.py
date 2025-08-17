# utils.py
import logging
import requests
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def send_telegram_alert(message: str):
    """
    Send alerts to Telegram (if enabled in config).
    If Telegram credentials are not provided, this does nothing.
    """
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        logger.debug("Telegram credentials not set. Skipping alert.")
        return

    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": Config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            logger.info("Telegram alert sent successfully.")
        else:
            logger.warning(f"Failed to send Telegram alert: {response.text}")
    except Exception as e:
        logger.error(f"Error sending Telegram alert: {e}")


def log_signal(symbol: str, direction: str, timeframe: str):
    """
    Log signals for monitoring and debugging.
    """
    msg = f"Signal detected: {symbol} | {direction} | {timeframe}"
    logger.info(msg)
    send_telegram_alert(msg)


def analyze_candles(candles, strategy_func):
    """
    Generic analyzer: applies a strategy function to candle data.
    candles: list of dicts (OHLC + indicators)
    strategy_func: function that returns (signal: str | None)
    """
    try:
        signal = strategy_func(candles)
        return signal
    except Exception as e:
        logger.error(f"Error analyzing candles: {e}")
        return None
