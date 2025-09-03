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

# Heartbeat interval (not needed explicitly with python-socketio, but kept for logging)
PING_INTERVAL = 10

# Socket.IO client
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

    # Step 1: Auth after connection
    auth_payload = {
        "sessionToken": sessionToken,
        "uid": uid,
        "lang": "en",
        "currentUrl": "cabinet/demo-quick-high-low",
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
    """Receive assets list from Pocket Option"""
    try:
        enabled_assets = [a["symbol"] for a in data if a.get("enabled")]
        update_symbols(enabled_assets)
        logging.info(f"[EVENT] Assets loaded: {len(enabled_assets)}")
    except Exception as e:
        logging.error(f"[ERROR] Failed to parse assets event: {e}")


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
    """
    Start Pocket Option Socket.IO in a separate thread.
    """
    t = threading.Thread(target=run_pocket_ws, args=(socketio_from_app,), daemon=True)
    t.start()


def get_dynamic_symbols():
    """Return the latest dynamic symbols"""
    global symbols
    return symbols


if __name__ == "__main__":
    logging.info("⚠️ Run this only from app.py, not directly.")
