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
        if mode["test_signals"]:  # ✅ only run when in TEST mode
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
# Background worker manager
def start_background_workers():
    """Start only the threads relevant to the current mode."""
    if mode["test_signals"]:
        logging.info("🚀 Starting TEST signal generator...")
        threading.Thread(
            target=generate_test_signals,
            args=(latest_signals, socketio, mode),
            daemon=True
        ).start()
    else:
        logging.info("🔌 Connecting to PocketOption WebSocket (LIVE mode)...")
        threading.Thread(
            target=start_pocket_ws,
            args=(socketio, latest_signals),   # ✅ pass socketio + list
            daemon=True
        ).start()

    # Always run fetching service regardless of mode
    threading.Thread(
        target=start_fetching,
        args=(SYMBOLS, TIMEFRAMES, socketio, latest_signals),
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
        {"symbol": "-", "signal": "No signals yet", "time": "-", "timeframe": "-"}
    ]
    return jsonify({
        "last_update": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "signals": signals_out,
        "mode": "TEST" if mode["test_signals"] else "LIVE"
    })

@app.route("/toggle_mode", methods=["POST"])
def toggle_mode():
    """Flip between TEST and LIVE and restart workers."""
    mode["test_signals"] = not mode["test_signals"]
    logging.info(f"Toggled mode -> {'TEST' if mode['test_signals'] else 'LIVE'}")

    # Restart background workers when mode changes
    start_background_workers()
    return jsonify({"mode": "TEST" if mode["test_signals"] else "LIVE"})

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

    # ✅ start appropriate background threads depending on mode
    start_background_workers()

    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
