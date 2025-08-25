# app.py
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

latest_signals = []  # shared list for dashboard

def start_fetching_wrapper(symbols, timeframes, socketio, latest_signals):
    """
    Wrapper around start_fetching to ensure emitted signals are also updated in latest_signals.
    """
    def emit_signal(signal):
        # Update the shared list in-place
        latest_signals.append(signal)
        logging.info(f"Emitting signal to frontend: {signal}")
        socketio.emit('new_signal', signal)

    # Call your original start_fetching, passing emit_signal as callback
    start_fetching(symbols, timeframes, Socketio, latest_signals)

# Start the live fetching thread
threading.Thread(
    target=start_fetching_wrapper, 
    args=(SYMBOLS, TIMEFRAMES, socketio, latest_signals),
    daemon=True
).start()

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
