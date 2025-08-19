# app.py
import threading
import time
import logging
from flask import Flask, render_template
from flask_cors import CORS
from data_fetcher import PocketOptionFetcher
from strategy import generate_signals
from telegram_utils import send_telegram_message
from config import SYMBOLS, TIMEFRAMES, TELEGRAM_CHAT_IDS

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow access from mobile browser
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

latest_signals = {}

# --- Initialize global fetcher instance ---
fetcher = PocketOptionFetcher(SYMBOLS, TIMEFRAMES)
fetcher.start()

def get_live_data(symbol, timeframe, length=50):
    """
    Fetch the latest candlestick data for a given symbol and timeframe.
    Falls back to empty DataFrame if no data yet.
    """
    import pandas as pd

    candles = fetcher.get_candles(symbol, timeframe)
    if not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles)
    return df.tail(length)  # return only the last N candles

def fetch_and_generate():
    """Fetch live data and generate signals continuously."""
    global latest_signals

    while True:
        try:
            signals = {}
            for symbol in SYMBOLS:
                signals[symbol] = {}
                for tf in TIMEFRAMES:
                    data = get_live_data(symbol, tf, length=50)
                    if not data.empty:
                        signal = generate_signals(data, symbol, tf)
                        signals[symbol][tf] = signal

                        # Send signal 30s before next candle close
                        if signal and "No Signal" not in signal:
                            now = time.time()
                            seconds_into_candle = int(now) % (int(tf[:-1]) * 60)
                            if seconds_into_candle >= (int(tf[:-1]) * 60 - 30):
                                for chat_id in TELEGRAM_CHAT_IDS:
                                    try:
                                        send_telegram_message(chat_id, signal)
                                    except Exception as send_err:
                                        logging.error(f"Failed to send Telegram message: {send_err}")
                    else:
                        signals[symbol][tf] = "No Data"

            latest_signals = signals
            logging.info("Signals updated successfully")

        except Exception as e:
            logging.error(f"Error fetching/generating signals: {e}")

        time.sleep(30)  # Recheck every 30s

@app.route("/")
def dashboard():
    return render_template("dashboard.html", signals=latest_signals)

if __name__ == "__main__":
    # Start background thread for fetching signals
    worker_thread = threading.Thread(target=fetch_and_generate, daemon=True)
    worker_thread.start()
    
    logging.info("Starting Flask app on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
