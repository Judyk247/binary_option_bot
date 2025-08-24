# app.py
import threading
import time
import logging
from flask import Flask, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from data_fetcher import start_fetching
from config import SYMBOLS, TIMEFRAMES, TELEGRAM_CHAT_IDS

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

latest_signals = {}

# Start the live fetching thread for Pocket Option data, dashboard, and Telegram alerts
threading.Thread(
    target=start_fetching, 
    args=(SYMBOLS, TIMEFRAMES, socketio, latest_signals),  # pass latest_signals
    daemon=True
).start()

@app.route("/")
def dashboard():
    """Render dashboard with the latest signals."""
    return render_template("dashboard.html", signals=latest_signals)

if __name__ == "__main__":
    logging.info("Starting Flask-SocketIO app on 0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
