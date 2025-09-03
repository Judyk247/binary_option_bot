import json
import time
import threading
import logging
import socketio

from credentials import uid, sessionToken, ACCOUNT_URL

# Pocket Option Socket.IO URL
POCKET_WS_URL = "https://events-po.com"

# Global dynamic symbols
symbols = []

# SocketIO instance injected from app.py
socketio_instance = None

# Socket.IO client
sio = socketio.Client(logger=False, engineio_logger=False, reconnection=True, reconnection_attempts=0, reconnection_delay=5)

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

    # Auth after connection
    auth_payload = {
        "sessionToken": sessionToken,
        "uid": uid,
        "lang": "en",
        "currentUrl": "cabinet",
        "isChart": 1
    }
    sio.emit("auth", auth_payload)
    logging.info("[AUTH] Auth message sent ✅")

    # Request assets list
    time.sleep(0.5)
    sio.emit("assets/get-assets", {})
    logging.info("[REQUEST] Requested assets list ✅")


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


def run_pocket_ws(socketio_from_app):
    global socketio_instance
    socketio_instance = socketio_from_app

    try:
        logging.info("🔌 Connecting to Pocket Option Socket.IO...")
        sio.connect(POCKET_WS_URL, transports=["websocket"], headers={"Origin": "https://m.pocketoption.com"})
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
