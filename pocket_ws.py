import json
import time
import websocket
from datetime import datetime
from threading import Thread

# Flask socketio instance will be injected from app.py
socketio = None  

from credentials import uid, sessionToken, ACCOUNT_URL

POCKET_WS_URL = "wss://events-po.com/socket.io/?EIO=4&transport=websocket"

# Keep track of subscribed assets for auto-resubscribe
subscribed_assets = []


def send_keepalive(ws):
    """Keep-alive ping loop (prevents server disconnect)."""
    while True:
        try:
            ws.send("2")  # Engine.IO ping
            print("[PING] Keep-alive sent")
        except Exception as e:
            print("[PING ERROR]", e)
            break
        time.sleep(20)  # send ping every 20s


def on_open(ws):
    logging.info("[OPEN] Connected to Pocket Option WebSocket")

    # Keep-alive ping loop
    def run_ping():
        while True:
            time.sleep(25)  # slightly less than server pingInterval (45s)
            try:
                ws.send("2")  # send Socket.IO ping
                logging.info("[PING] Keep-alive sent")
            except Exception as e:
                logging.error(f"[PING ERROR] {e}")
                break

    threading.Thread(target=run_ping, daemon=True).start()

    # Send namespace open
    try:
        ws.send("40")
        logging.info("[SEND] Namespace open (40) ✅")
    except Exception as e:
        logging.error(f"[ERROR] Failed to send namespace open: {e}")

    # Send authentication
    try:
        auth_payload = [
            "auth",
            {
                "sessionToken": sessionToken,
                "uid": uid,
                "lang": "en",
                "currentUrl": ACCOUNT_URL,  # ✅ real account
                "isChart": 1
            }
        ]
        ws.send("42" + json.dumps(auth_payload))
        logging.info("[SEND] auth message sent ✅")
    except Exception as e:
        logging.error(f"[ERROR] Failed to send auth: {e}")

    # Request assets list (example extra init call)
    try:
        ws.send('42["assets/get-assets",{}]')
        logging.info("[SEND] Requested assets list (after connect) ✅")
    except Exception as e:
        logging.error(f"[ERROR] Failed to request assets: {e}")


def on_message(ws, message):
    logging.info(f"[RAW] {message}")

    # Handle Socket.IO heartbeat (pong from server)
    if message == "3":
        logging.debug("[HEARTBEAT] Pong received ✅")
        return

    # Handle handshake
    if message.startswith("0{"):
        logging.info("[HANDSHAKE] Received Socket.IO handshake ✅")
        return

    # Handle namespace open confirmation
    if message == "40":
        logging.info("[NAMESPACE] Namespace open confirmed ✅")
        return

    # Handle custom events
    if message.startswith("42"):
        try:
            payload = json.loads(message[2:])
            event, data = payload[0], payload[1]
            logging.info(f"[EVENT] {event} => {data}")
        except Exception as e:
            logging.error(f"[ERROR] Failed to parse event: {e}")


def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] Connection closed:", close_status_code, close_msg)


def on_error(ws, error):
    print("[ERROR]", error)


def run_ws():
    while True:  # 24/7 auto-reconnect
        try:
            ws = websocket.WebSocketApp(
                POCKET_WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_close=on_close,
                on_error=on_error,
                header=["Origin: https://m.pocketoption.com"]  # required header
            )
            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)


def start_pocket_ws(sio):
    """Called from app.py to start PocketOption WS in background."""
    global socketio
    socketio = sio

    t = Thread(target=run_ws, daemon=True)
    t.start()


if __name__ == "__main__":
    print("⚠️ Run this only from app.py, not directly.")
