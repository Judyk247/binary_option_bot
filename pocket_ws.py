import websocket
import json
import threading

POCKET_WS_URL = "wss://ws.pocketoption.com/socket.io/?EIO=3&transport=websocket"
SESSION_TOKEN = "b651d1bb804319e18d46104a66f13197"
USER_ID = 107618624

def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Send authentication
    auth_msg = f'42["auth",{{"sessionToken":"{SESSION_TOKEN}","uid":"{USER_ID}","lang":"en","currentUrl":"cabinet/demo-quick-high-low","isChart":1}}]'
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

                # Subscribe to all pairs
                for asset in assets:
                    ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                    ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":60}}]')
                    ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":180}}]')
                    ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":300}}]')
                print(f"[SUBSCRIBE] Subscribed to {len(assets)} assets 🔥")

            elif event == "ticks":
                print("[TICK]", payload)

            elif event == "candles":
                print("[CANDLE]", payload)

        except Exception as e:
            print("[ERROR parsing]", e)

def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] Connection closed:", close_status_code, close_msg)

def on_error(ws, error):
    print("[ERROR]", error)

def run_ws():
    ws = websocket.WebSocketApp(
        POCKET_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error
    )
    ws.run_forever()

if __name__ == "__main__":
    run_ws()
