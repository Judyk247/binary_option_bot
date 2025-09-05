import json
import time
import threading
import logging
import socketio

def setup_debug_logger():
    """Enable full debug logging for Socket.IO and our app."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    logging.getLogger("socketio").setLevel(logging.DEBUG)
    logging.getLogger("engineio").setLevel(logging.DEBUG)

    logging.debug("[DEBUG] Debug logger initialized")

from credentials import uid, sessionToken, ACCOUNT_URL

# Pocket Option Socket.IO URL
POCKET_WS_URL = "https://events-po.com"

# Global dynamic symbols
symbols = []

# SocketIO instance injected from app.py
socketio_instance = None

import logging
sio = socketio.Client(
    logger=logging.getLogger("socketio"),
    engineio_logger=logging.getLogger("engineio"),
    reconnection=True,
    reconnection_attempts=0,
    reconnection_delay=5
)

# Store market data locally (for reference, optional)
market_data = {}

def update_symbols(new_symbols):
    global symbols
    symbols = new_symbols
    logging.info(f"[SYMBOLS] Updated dynamic symbols: {symbols}")
    if socketio_instance:
        socketio_instance.emit("symbols_update", {"symbols": symbols})


@sio.event
def connect():
    logging.info("[CONNECT] Connected to Pocket Option Socket.IO")

    # 🔑 Send auth right after connection
    sio.emit("auth", {
        "sessionToken": sessionToken,
        "uid": uid,
        "lang": "en",
        "currentUrl": "cabinet",  # <-- update this if your capture changes
        "isChart": 1
    })
    logging.info("[AUTH] Auth message sent ✅")


# ✅ Handle auth success
@sio.on("auth/success")
def on_auth_success(data=None):
    logging.info("[AUTH] Authenticated successfully ✅")
    # Immediately send counters/all after auth
    socketio.emit("counters/all", {})
    logging.info("[SUBSCRIBE] Sent counters/all request ✅")


# ✅ Handle counters/all/success confirmation
@sio.on("counters/all/success")
def on_counters_success(data):
    logging.info(f"[SUBSCRIBE CONFIRMED] counters/all → {data}")


@sio.event
def disconnect():
    logging.warning("[DISCONNECT] Connection closed")


@sio.on("assets")
def handle_assets(data):
    """Receive assets list and subscribe to ticks & candles."""
    try:
        enabled_assets = [a.get("symbol") for a in data if a.get("enabled") and a.get("symbol")]

        if not enabled_assets:
            logging.warning("[EVENT] No enabled assets found.")
            return

        update_symbols(enabled_assets)
        logging.info(f"[EVENT] Assets loaded: {len(enabled_assets)} -> {enabled_assets}")

        # Subscribe to ticks and candles for each asset
        for asset in enabled_assets:
            try:
                sio.emit("subscribe", {"type": "ticks", "asset": asset})
                for period in [60, 180, 300]:  # 1m, 3m, 5m
                    sio.emit("subscribe", {"type": "candles", "asset": asset, "period": period})
            except Exception as sub_err:
                logging.error(f"[ERROR] Subscription failed for {asset}: {sub_err}")

        logging.info(f"[SUBSCRIBE] Subscribed to {len(enabled_assets)} assets: {enabled_assets} 🔥")

    except Exception as e:
        logging.error(f"[ERROR] Failed to handle assets: {e}")

@sio.on("ticks")
def handle_ticks(data):
    """Optional local store for ticks."""
    asset = data.get("asset")
    if asset:
        market_data.setdefault(asset, {}).setdefault("ticks", []).append({"time": data["time"], "price": data["price"]})


@sio.on("candles")
def handle_candles(data):
    """Optional local store for candles."""
    asset = data.get("asset")
    period = data.get("period")
    if asset and period:
        market_data.setdefault(asset, {}).setdefault("candles", {}).setdefault(period, []).append(data)

@sio.on("*")
def catch_all(event, data=None):
    """Catch-all debug logger for every incoming event."""
    try:
        if data is not None:
            logging.debug(f"[CATCH-ALL] Event: {event} | Data: {str(data)[:500]}")
        else:
            logging.debug(f"[CATCH-ALL] Event: {event} (no data)")
    except Exception as e:
        logging.error(f"[CATCH-ALL ERROR] {e}")


def run_pocket_ws(socketio_from_app):
    global socketio_instance
    socketio_instance = socketio_from_app

    try:
        logging.info("🔌 Connecting to Pocket Option Socket.IO...")
        sio.connect(
    POCKET_WS_URL,
    transports=["websocket"],
    headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Origin": "https://m.pocketoption.com",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,my-ZG;q=0.8,my;q=0.7",
    }
)
        sio.wait()
    except Exception as e:
        logging.error(f"[FATAL ERROR] {e}")
        logging.info("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)
        run_pocket_ws(socketio_from_app)


def start_pocket_ws(socketio_from_app):
    """Start Pocket Option Socket.IO in a separate thread."""
    t = threading.Thread(target=run_pocket_ws, args=(socketio_from_app,), daemon=True)
    t.start()


def get_dynamic_symbols():
    """Return the latest dynamic symbols"""
    global symbols
    return symbols


if __name__ == "__main__":
    logging.info("⚠️ Run this only from app.py, not directly.")
