import os
import json
import time
import websocket
from datetime import datetime
from threading import Thread

# We will inject socketio + mode from app.py instead of importing app directly
socketio = None
mode = None  

from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL

POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"


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
                ws.send('42["getAssets", {}]')
                print("[SEND] Requested all assets list")

            elif event == "assets":
                print("[RECV] Assets list received ✅")
                assets = [a["symbol"] for a in payload if a.get("enabled")]

                # Subscribe to all pairs automatically
                for asset in assets:
                    for period in [60, 180, 300]:  # 1m, 3m, 5m
                        ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":{period}}}]')
                    ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                print(f"[SUBSCRIBE] Subscribed to {len(assets)} assets 🔥")

            elif event == "ticks":
                # Handle ticks data
                symbol = payload.get("asset")
                price = payload.get("price")
                print(f"[TICK] {symbol}: {price}")

            elif event == "candles":
                # Handle candle data
                symbol = payload.get("asset")
                timeframe = f"{payload.get('period')//60}m"
                candle_time = datetime.utcfromtimestamp(payload["time"]).strftime("%Y-%m-%d %H:%M:%S")
                close_price = payload.get("close")

                print(f"[CANDLE] {symbol} {timeframe} Close={close_price} at {candle_time}")

                # === Stub: emit signal (later plug strategy logic here) ===
                signal = {
                    "symbol": symbol,
                    "signal": "BUY",   # placeholder
                    "timeframe": timeframe,
                    "time": candle_time
                }
                if socketio:
                    socketio.emit("new_signal", signal)

        except Exception as e:
            print("[ERROR parsing message]", e)


def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] Connection closed:", close_status_code, close_msg)


def on_error(ws, error):
    print("[ERROR]", error)


def run_ws():
    while True:  # 24/7 auto-reconnect
        try:
            # Only run when LIVE mode is active
            if mode and not mode.get("test_signals", True):
                ws = websocket.WebSocketApp(
                    POCKET_WS_URL,
                    on_open=on_open,
                    on_message=on_message,
                    on_close=on_close,
                    on_error=on_error,
                    header=["Origin: https://m.pocketoption.com"]  # required header
                )
                ws.run_forever()
            else:
                print("[POCKET_WS] Skipping connection (TEST mode active).")
                time.sleep(5)
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)


def start_pocket_ws(sio, runtime_mode):
    """
    Called from app.py to start PocketOption WS in background.
    We inject socketio + mode dict to avoid circular imports.
    """
    global socketio, mode
    socketio = sio
    mode = runtime_mode

    t = Thread(target=run_ws, daemon=True)
    t.start()


if __name__ == "__main__":
    print("⚠️ Run this only from app.py, not directly.")
