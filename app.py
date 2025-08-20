# app.py
import threading
import time
import logging
from flask import Flask, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
from data_fetcher import PocketOptionFetcher
from strategy import generate_signals
from telegram_utils import send_telegram_message
from config import SYMBOLS, TIMEFRAMES, TELEGRAM_CHAT_IDS, PO_API_BASE, PO_EMAIL, PO_PASSWORD

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Initialize SocketIO
socketio = SocketIO(app, async_mode="eventlet")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

latest_signals = {}

# --- Initialize global fetcher instance ---
fetcher = PocketOptionFetcher(
    email=PO_EMAIL,
    password=PO_PASSWORD,
    api_base=PO_API_BASE,
    symbols=SYMBOLS,
    timeframes=TIMEFRAMES
)
fetcher.start()

def get_live_data(symbol, timeframe, length=50):
    import pandas as pd
    candles = fetcher.get_candles(symbol, timeframe)
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(candles)
    return df.tail(length)

def fetch_and_generate():
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

                        if signal and "No Signal" not in signal:
                            now = time.time()
                            seconds_into_candle = int(now) % (int(tf[:-1]) * 60)
                            if seconds_into_candle >= (int(tf[:-1]) * 60 - 30):
                                for chat_id in TELEGRAM_CHAT_IDS:
                                    try:
                                        send_telegram_message(chat_id, signal)
                                    except Exception as send_err:
                                        logging.error(f"Failed to send Telegram message: {send_err}")

                        # Push live update to dashboard
                        socketio.emit(
                            "new_signal",
                            {"symbol": symbol, "timeframe": tf, "signal": signal},
                            broadcast=True
                        )
                    else:
                        signals[symbol][tf] = "No Data"

            latest_signals = signals
            logging.info("Signals updated successfully")

        except Exception as e:
            logging.error(f"Error fetching/generating signals: {e}")

        time.sleep(30)

@app.route("/")
def dashboard():
    return render_template("dashboard.html", signals=latest_signals)

if __name__ == "__main__":
    worker_thread = threading.Thread(target=fetch_and_generate, daemon=True)
    worker_thread.start()
    logging.info("Starting Flask-SocketIO app on 0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)  # ✅ Debug enabled
