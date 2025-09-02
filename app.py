import threading
import logging
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from data_fetcher import start_fetching
from datetime import datetime, timezone
from config import SYMBOLS, TIMEFRAMES, TELEGRAM_CHAT_IDS
from credentials import sessionToken, uid, POCKET_WS_URL, ACCOUNT_URL

# 👇 Import PocketOption WebSocket
from pocket_ws import start_pocket_ws  

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
# Background worker manager
def start_background_workers():
    """Start PocketOption WebSocket + data fetcher in LIVE mode."""
    logging.info("🔌 Connecting to PocketOption WebSocket (LIVE mode)...")
    threading.Thread(
        target=start_pocket_ws,
        args=(socketio, POCKET_WS_URL, sessionToken, uid, ACCOUNT_URL),  # 👈 pass URL + creds
        daemon=True
    ).start()
# -----------------------------


@app.route("/")
def dashboard():
    """Render dashboard shell only (table filled by AJAX)."""
    logging.info("Rendering dashboard page")
    return render_template("dashboard.html")


@app.route("/signals_data")
def signals_data():
    """Return latest signals as JSON for AJAX polling."""
    signals_out = latest_signals if latest_signals else [
        {
            "symbol": "-",
            "signal": "No signals yet",
            "confidence": 0,
            "time": "-",
            "timeframe": "-"
        }
    ]
    return jsonify({
        "last_update": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "signals": signals_out,
        "mode": "LIVE"
    })


# -----------------------------
# Emit signals immediately to new dashboard clients
@socketio.on("connect")
def on_connect():
    logging.info("Client connected, sending current signals...")
    for sig in latest_signals:
        socketio.emit("new_signal", sig)
# -----------------------------


if __name__ == "__main__":
    logging.info("Starting Flask-SocketIO app on 0.0.0.0:5000")

    # ✅ Always start background workers in LIVE mode
    start_background_workers()

    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
