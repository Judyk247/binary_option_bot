import json
import time
import websocket
from datetime import datetime
from threading import Thread

# Flask socketio instance will be injected from app.py
socketio = None  

from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL

POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# Hardcoded default forex pairs (no crypto, no stocks)
DEFAULT_SYMBOLS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "NZD/USD",
    "USD/CAD", "EUR/GBP", "EUR/JPY", "GBP/JPY", "AUD/JPY", "NZD/JPY",
    "EUR/AUD", "EUR/NZD", "EUR/CAD", "EUR/CHF", "GBP/AUD", "GBP/NZD",
    "GBP/CAD", "GBP/CHF", "AUD/NZD", "AUD/CAD", "AUD/CHF", "NZD/CAD",
    "NZD/CHF", "CAD/CHF", "CAD/JPY", "CHF/JPY", "EUR/SEK", "EUR/NOK"
]


def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Send authentication
    auth_msg = f'42["auth",{{"sessionToken":"{POCKET_SESSION_TOKEN}","uid":"{POCKET_USER_ID}","lang":"en","currentUrl":"{POCKET_ACCOUNT_URL}","isChart":1}}]'
    ws.send(auth_msg)
    print("[SEND] Auth message sent ✅")


def on_message(ws, message):
    global socketio
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None

            if event == "auth_success":
                print("[AUTH] Authentication successful ✅")

                # Subscribe only to default forex pairs (ticks only)
                for asset in DEFAULT_SYMBOLS:
                    ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                print(f"[SUBSCRIBE] Subscribed to {len(DEFAULT_SYMBOLS)} forex pairs 🔥")

            elif event == "ticks":
                # Handle ticks data
                symbol = payload.get("asset")
                price = payload.get("price")
                tick_time = datetime.utcfromtimestamp(payload["time"]).strftime("%Y-%m-%d %H:%M:%S")
                print(f"[TICK] {symbol}: {price} at {tick_time}")

                # === Stub: Forward tick to bot (bot will aggregate into timeframes) ===
                tick_data = {
                    "symbol": symbol,
                    "price": price,
                    "time": tick_time
                }
                if socketio:
                    socketio.emit("new_tick", tick_data)

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
    """
    Called from app.py to start PocketOption WS in background.
    We inject socketio only (no test/live toggle anymore).
    """
    global socketio
    socketio = sio

    t = Thread(target=run_ws, daemon=True)
    t.start()


if __name__ == "__main__":
    print("⚠️ Run this only from app.py, not directly.")
