import json
import time
import websocket
from datetime import datetime
from threading import Thread

# Flask socketio instance will be injected from app.py
socketio = None  

from credentials import POCKET_USER_ID, POCKET_SECRET

POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"


def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Send user_init authentication (id + secret)
    auth_msg = f'42["user_init",{{"id":{POCKET_USER_ID},"secret":"{POCKET_SECRET}"}}]'
    ws.send(auth_msg)
    print("[SEND] user_init message sent ✅")


def on_message(ws, message):
    global socketio
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None

            if event in ["user_init", "user_data"]:
                print(f"[AUTH] Authentication successful ✅ Event={event}")

                # Request full asset list dynamically
                ws.send('42["getAssets", {}]')
                print("[SEND] Requested assets list from PocketOption")

            elif event == "assets":
                print("[RECV] Assets list received ✅")

                # Filter only enabled forex assets
                assets = [
                    a["symbol"] for a in payload
                    if a.get("enabled") and a.get("type") == "forex"
                ]

                # Subscribe dynamically to ticks for all forex pairs
                for asset in assets:
                    ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                print(f"[SUBSCRIBE] Subscribed to {len(assets)} forex pairs 🔥")

            elif event == "ticks":
                # Handle ticks data
                symbol = payload.get("asset")
                price = payload.get("price")
                tick_time = datetime.utcfromtimestamp(payload["time"]).strftime("%Y-%m-%d %H:%M:%S")
                print(f"[TICK] {symbol}: {price} at {tick_time}")

                tick_data = {
                    "symbol": symbol,
                    "price": price,
                    "time": tick_time
                }
                if socketio:
                    socketio.emit("new_tick", tick_data)

            else:
                print("[DEBUG] Unhandled event:", event, payload)

        except Exception as e:
            print("[ERROR parsing message]", e)


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
