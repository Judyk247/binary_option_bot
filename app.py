import threading
import logging
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from data_fetcher import start_fetching
from datetime import datetime, timezone
from config import SYMBOLS, TIMEFRAMES, TELEGRAM_CHAT_IDS
import random
import time

# 👇 NEW IMPORT
from pocket_ws import start_pocket_ws  

# -----------------------------
# Runtime toggle (default = Test)
mode = {"test_signals": True}
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
MAX_SIGNALS = 50     # Keep only the last 50

# -----------------------------
# Test signal generator for debug mode
def generate_test_signals(latest_signals, socketio, mode):
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    timeframes = ["1m", "3m", "5m"]
    while True:
        if mode["test_signals"]:  # only run when in test mode
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

                    # Keep size limited
                    if len(latest_signals) > MAX_SIGNALS:
                        latest_signals.pop(0)

                    socketio.emit("new_signal", new_signal)
        time.sleep(5)
# -----------------------------

# -----------------------------
# Start background threads
threading.Thread(
    target=generate_test_signals,
    args=(latest_signals, socketio, mode),
    daemon=True
).start()

threading.Thread(
    target=start_fetching,
    args=(SYMBOLS, TIMEFRAMES, socketio, latest_signals),
    daemon=True
).start()

# 👇 NEW: Start PocketOption WebSocket in background
threading.Thread(
    target=start_pocket_ws,
    daemon=True
).start()
# -----------------------------

@app.route("/")
def dashboard():
    """Render dashboard shell only (table filled by AJAX)."""
    logging.info("Rendering dashboard page")
    return render_template("dashboard.html")
