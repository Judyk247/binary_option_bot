# pocket_ws.py
import websocket
import json
import threading
import time

# Your session token and UID
SESSION_TOKEN = "b651d1bb804319e18d46104a66f13197"
UID = "107618624"

# WebSocket endpoint
WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Step 1: Authenticate immediately after connection
    auth_msg = [
        "auth",
        {
            "sessionToken": SESSION_TOKEN,
            "uid": UID,
            "lang": "en",
            "currentUrl": "cabinet/demo-quick-high-low",  # live/demo environment
            "isChart": 1
        }
    ]

    ws.send("42" + json.dumps(auth_msg))
    print("[SEND] Auth message sent ✅")

def on_message(ws, message):
    print("[RECV]", message)

    # Example: handle ping
    if message == "2":
        ws.send("3")
        print("[PING] -> [PONG]")

def on_close(ws, close_status_code, close_msg):
    print(f"[CLOSE] Connection closed: {close_status_code} {close_msg}")

def on_error(ws, error):
    print(f"[ERROR] {error}")

def run_ws():
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error
    )
    ws.run_forever(ping_interval=40, ping_timeout=10)

if __name__ == "__main__":
    run_ws()
