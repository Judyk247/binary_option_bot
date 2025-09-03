import json
import time
import threading
import logging
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd
import socketio

from credentials import sessionToken, uid, ACCOUNT_URL
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from config import TELEGRAM_CHAT_IDS

# Pocket Option Socket.IO URL
POCKET_IO_URL = "https://events-po.com"

# Store incoming data for all assets and timeframes
market_data = defaultdict(lambda: {"ticks": [], "candles": defaultdict(list)})

# Supported candle periods in seconds
CANDLE_PERIODS = [60, 180, 300]  # 1m, 3m, 5m

# Dynamic symbols
symbols = []

# Socket.IO instance injected from app.py
socketio_instance = None

# Python-socketio client
sio = socketio.Client(logger=False, engineio_logger=False, reconnection=True, reconnection_attempts=0, reconnection_delay=5)


def update_symbols(new_symbols):
    global symbols
    symbols = new_symbols
    logging.info(f"[SYMBOLS] Updated dynamic symbols: {symbols}")
    if socketio_instance:
        socketio_instance.emit("symbols_update", {"symbols": symbols})


@sio.event
def connect():
    logging.info("[CONNECT] Connected to Pocket Option Socket.IO")

    # Step 1: Authenticate
    auth_payload = {
        "sessionToken": sessionToken,
        "uid": uid,
        "lang": "en",
        "currentUrl": "cabinet",
        "isChart": 1
    }
    sio.emit("auth", auth_payload)
    logging.info("[AUTH] Auth message sent ✅")

    # Step 2: Request assets list after short delay
    time.sleep(0.5)
    sio.emit("assets/get-assets", {})
    logging.info("[REQUEST] Requested assets list ✅")


@sio.event
def disconnect():
    logging.warning("[DISCONNECT] Connection closed")


@sio.on("assets")
def handle_assets(data):
    """Receive assets list from Pocket Option and subscribe to ticks/candles."""
    try:
        enabled_assets = [a["symbol"] for a in data if a.get("enabled")]
        update_symbols(enabled_assets)
        logging.info(f"[EVENT] Assets loaded: {len(enabled_assets)}")

        # Subscribe to ticks and candles for each asset
        for asset in enabled_assets:
            sio.emit("subscribe", {"type": "ticks", "asset": asset})
            for period in CANDLE_PERIODS:
                sio.emit("subscribe", {"type": "candles", "asset": asset, "period": period})
        logging.info(f"[SUBSCRIBE] Subscribed to {len(enabled_assets)} assets 🔥")

    except Exception as e:
        logging.error(f"[ERROR] Failed to handle assets: {e}")


@sio.on("ticks")
def handle_ticks(data):
    try:
        asset = data["asset"]
        tick = {"time": data["time"], "price": data["price"]}
        market_data[asset]["ticks"].append(tick)
    except Exception as e:
        logging.error(f"[ERROR] Failed to parse tick: {e}")


@sio.on("candles")
def handle_candles(data):
    try:
        asset = data["asset"]
        period = data["period"]
        candle = {
            "time": data["time"],
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data["volume"],
        }
        market_data[asset]["candles"][period].append(candle)
    except Exception as e:
        logging.error(f"[ERROR] Failed to parse candle: {e}")


def get_market_data():
    return market_data


def get_dynamic_symbols(wait_for_symbols=True):
    global symbols
    if wait_for_symbols:
        wait_time = 0
        while not symbols and wait_time < 10:
            time.sleep(0.5)
            wait_time += 0.5
    return symbols.copy()


def tf_to_seconds(tf):
    return int(tf[:-1]) * 60


def start_fetching(timeframes, socketio_from_app, latest_signals):
    """
    Continuously analyze signals from candles & emit updates to dashboard via SocketIO.
    """
    global socketio_instance
    socketio_instance = socketio_from_app

    while True:
        current_symbols = get_dynamic_symbols()
        for symbol in current_symbols:
            for tf in timeframes:
                candles = market_data[symbol]["candles"].get(tf_to_seconds(tf), [])
                
                if not candles:
                    # Emit a default HOLD signal for symbols without candles yet
                    signal_data = {
                        "symbol": symbol,
                        "signal": "HOLD",
                        "confidence": 0,
                        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "timeframe": tf
                    }
                    # Update latest_signals
                    latest_signals[:] = [s for s in latest_signals if not (s["symbol"] == symbol and s["timeframe"] == tf)]
                    latest_signals.append(signal_data)
                    socketio_from_app.emit("new_signal", signal_data)
                    continue

                df = pd.DataFrame(candles)
                result = analyze_candles(df)

                if isinstance(result, tuple):
                    signal_value, confidence = result
                else:
                    signal_value = result
                    confidence = 100

                signal_data = {
                    "symbol": symbol,
                    "signal": signal_value if signal_value else "HOLD",
                    "confidence": confidence,
                    "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "timeframe": tf
                }

                # Update latest_signals
                latest_signals[:] = [s for s in latest_signals if not (s["symbol"] == symbol and s["timeframe"] == tf)]
                latest_signals.append(signal_data)

                # Emit to frontend
                socketio_from_app.emit("new_signal", signal_data)

                # Telegram alerts
                if signal_value in ["BUY", "SELL"]:
                    for chat_id in TELEGRAM_CHAT_IDS:
                        if chat_id:
                            try:
                                send_telegram_message(chat_id, f"{symbol} {tf} signal: {signal_value} ({confidence}%)")
                            except Exception as e:
                                logging.error(f"[TELEGRAM ERROR] {e}")

        time.sleep(5)


def run_socketio():
    try:
        logging.info("🔌 Connecting to Pocket Option Socket.IO...")
        sio.connect(POCKET_IO_URL, transports=["websocket"], headers={"Origin": "https://m.pocketoption.com"})
        sio.wait()
    except Exception as e:
        logging.error(f"[FATAL ERROR] {e}")
        logging.info("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)
        run_socketio()


def start_data_fetcher():
    t = threading.Thread(target=run_socketio, daemon=True)
    t.start()


if __name__ == "__main__":
    start_data_fetcher()
