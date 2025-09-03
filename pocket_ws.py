import json
import time
import websocket
import threading
import logging

from credentials import uid, sessionToken, ACCOUNT_URL

POCKET_WS_URL = "wss://events-po.com/socket.io/?EIO=4&transport=websocket"

# Dynamically loaded symbols
symbols = []

# SocketIO instance injected from app.py
socketio_instance = None

# Heartbeat ping interval
PING_INTERVAL = 20


def send_heartbeat(ws):
    """Send periodic ping to keep connection alive."""
    while True:
        try:
            ws.send("2")  # Standard Socket.IO ping
            logging.debug("[PING] Keep-alive sent")
        except Exception as e:
            logging.error(f"[PING ERROR] {e}")
            break
        time.sleep(PING_INTERVAL)


def on_open(ws):
    logging.info("[OPEN] Connected to Pocket Option WebSocket")

    # Send namespace open
    ws.send("40")
    logging.info("[SEND] Namespace open (40) ✅")

    # Send authentication
    auth_payload = [
        "auth",
        {
            "sessionToken": sessionToken,
            "uid": uid,
            "lang": "en",
            "currentUrl": ACCOUNT_URL,
            "isChart": 1
        }
    ]
    ws.send("42" + json.dumps(auth_payload))
    logging.info("[SEND] Auth message sent ✅")

    # Request assets list
    ws.send('42["assets/get-assets",{}]')
    logging.info("[SEND] Requested assets list ✅")


def on_message(ws, message):
    global symbols

    # Handle Socket.IO heartbeat
    if message == "3":
        return

    # Handle handshake
    if message.startswith("0{"):
        return

    # Namespace open confirmation
    if message == "40":
        return

    # Custom events
    if message.startswith("42"):
        try:
            payload = json.loads(message[2:])
            event, data = payload[0], payload[1]

            if event == "assets":
                logging.info(f"[EVENT] {event} => {len(data)} assets loaded")
                symbols = [a["symbol"] for a in data if a.get("enabled")]
                logging.info(f"[DEBUG] Dynamic symbols updated: {symbols}")

            # Emit symbols update via SocketIO if needed
            if socketio_instance:
                socketio_instance.emit("symbols_update", {"symbols": symbols})

        except Exception as e:
            logging.error(f"[ERROR] Failed to parse event: {e}")


def on_close(ws, close_status_code, close_msg):
    logging.warning(f"[CLOSE] Connection closed: {close_status_code} - {close_msg}")


def on_error(ws, error):
    logging.error(f"[ERROR] {error}")


def run_ws(socketio, POCKET_WS_URL, sessionToken, uid, ACCOUNT_URL):
    while True:
        try:
            ws = websocket.WebSocketApp(
                POCKET_WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_close=on_close,
                on_error=on_error,
                header=["Origin: https://m.pocketoption.com"]
            )

            threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()
            ws.run_forever()
        except Exception as e:
            logging.error(f"[FATAL ERROR] {e}")
        logging.info("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)


def start_pocket_ws(socketio, POCKET_WS_URL, sessionToken, uid, ACCOUNT_URL):
    """
    Starts Pocket Option WebSocket in a separate thread.
    """
    global socketio_instance
    socketio_instance = socketio

    t = threading.Thread(
        target=run_ws,
        args=(socketio, POCKET_WS_URL, sessionToken, uid, ACCOUNT_URL),
        daemon=True
    )
    t.start()


def get_dynamic_symbols():
    """Return the latest dynamic symbols for use by data_fetcher."""
    global symbols
    return symbols


if __name__ == "__main__":
    print("⚠️ Run this only from app.py, not directly.")
