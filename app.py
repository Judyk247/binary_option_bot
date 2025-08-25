import threading
import logging
from flask import Flask, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from data_fetcher import start_fetching
from datetime import datetime, timezone
from config import SYMBOLS, TIMEFRAMES, TELEGRAM_CHAT_IDS
import random
import time

# -----------------------------
# TOGGLE: Set True for testing dashboard with fake signals
# Set False for live Pocket Option signals
DEBUG_TEST_SIGNALS = True
# -----------------------------

# Flask app setup
app = Flask(__name__)
CORS(app)
app.config["TEMPLATES_AUTO_RELOAD"] = True
socketio = SocketIO(app, async_mode="eventlet")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

latest_signals = []  # Store latest signals for dashboard

# -----------------------------
# Test signal generator for debug mode
def generate_test_signals(latest_signals, socketio):
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    timeframes = ["1m", "3m", "5m"]
    while True:
        for symbol in symbols:
            for tf in timeframes:
                signal = random.choice(["BUY", "SELL", "HOLD"])
                new_signal = {
                    "symbol": symbol,
                    "signal": signal,
                    "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "timeframe": tf
                }
                latest_signals.append(new_signal)
                socketio.emit("new_signal", new_signal)
        time.sleep(5)
# -----------------------------

# -----------------------------
# Start appropriate background thread
if DEBUG_TEST_SIGNALS:
    threading.Thread(
        target=generate_test_signals,
        args=(latest_signals, socketio),
        daemon=True
    ).start()
else:
    threading.Thread(
        target=start_fetching, 
        args=(SYMBOLS, TIMEFRAMES, socketio, latest_signals),
        daemon=True
    ).start()
# -----------------------------

@app.route("/")
def dashboard():
    """Render dashboard with the latest signals and current time."""
    logging.info(f"Rendering dashboard with {len(latest_signals)} signals")
    return render_template(
        "dashboard.html",
        signals=latest_signals,
        now=datetime.now(timezone.utc)
    )

if __name__ == "__main__":
    logging.info("Starting Flask-SocketIO app on 0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
