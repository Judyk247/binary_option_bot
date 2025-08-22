import os
import json
import time
import websocket
from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL

POCKET_WS_URL = wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket

def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Send authentication
    auth_msg = f'42["auth",{{"sessionToken":"{POCKET_SESSION_TOKEN}","uid":"{POCKET_USER_ID}","lang":"en","currentUrl":"{POCKET_ACCOUNT_URL}","isChart":1}}]'
    ws.send(auth_msg)
    print("[SEND] Auth message sent ✅")

    # Request assets list
    ws.send('42["getAssets", {}]')
    print("[SEND] Requested all assets list")

def on_message(ws, message):
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None

            if event == "assets":
                print("[RECV] Assets list received ✅")
                assets = [a["symbol"] for a in payload if a.get("enabled")]

                # Subscribe to all pairs automatically
                for asset in assets:
                    for period in [60, 180, 300]:  # 1m, 3m, 5m
                        ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":{period}}}]')
                    ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                print(f"[SUBSCRIBE] Subscribed to {len(assets)} assets 🔥")

            elif event == "ticks":
                # Handle ticks data (ready for trading logic)
                print("[TICK]", payload)

            elif event == "candles":
                # Handle candle data (ready for trading logic)
                print("[CANDLE]", payload)

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
                on_error=on_error
            )
            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    run_ws()
