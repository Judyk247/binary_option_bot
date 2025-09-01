import json
import time
import websocket
from datetime import datetime
from threading import Thread

# Flask socketio instance will be injected from app.py
socketio = None  

from credentials import uid, sessionToken

POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

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
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Step 1: open namespace
    ws.send("40")
    print("[SEND] Namespace open (40) ✅")

    time.sleep(1)  # small delay

    # Step 2: correct authentication
    auth_payload = {
        "sessionToken": sessionToken,
        "uid": uid,
        "lang": "en",
        "currentUrl": ACCOUNT_URL,  # e.g. "cabinet"
        "isChart": 1
    }
    auth_msg = f'42["auth",{json.dumps(auth_payload)}]'
    ws.send(auth_msg)
    print("[SEND] auth message sent ✅")

    time.sleep(1)

    # Step 3: request assets list
    ws.send('42["getAssets", {}]')
    print("[SEND] Requested assets list")

def on_message(ws, message):
    global socketio

    # Always log raw message
    print(f"[RAW] {message}")

    try:
        # ---- Socket.IO handshake ----
        if message.startswith("0{"):
            print("[HANDSHAKE] Received Socket.IO handshake ✅")
            ws.send("40")  # open default namespace
            print("[SEND] Sent '40' (open namespace)")

        # ---- Namespace opened ----
        elif message == "40":
            print("[NAMESPACE] Default namespace opened ✅")
            # Send user_init immediately after namespace is open
            ws.send(json.dumps(["user_init", {
                "sessionToken": sessionToken,
                "uid": uid,
                "lang": "en"
            }]).replace("[", '42[', 1))
            print("[SEND] user_init message sent ✅")

        # ---- Server ping ----
        elif message == "2":
            print("[PING] Received ping → sending pong (3)")
            ws.send("3")

        # ---- Server disconnect ----
        elif message == "41":
            print("[DISCONNECT] Server closed namespace ❌")

        # ---- Socket.IO event messages ----
        elif message.startswith("42"):
            try:
                data = json.loads(message[2:])
                event = data[0]
                payload = data[1] if len(data) > 1 else None
                print(f"[EVENT] {event} | Payload: {payload}")

                if event == "user_init":
                    print(f"[AUTH-STEP1] Server acknowledged user_init ✅ Payload={payload}")

                elif event == "user_data":
                    print(f"[AUTH-STEP2] Authentication confirmed 🎉 User data received")
                    print(f"   UID: {payload.get('uid')}, Balance: {payload.get('balance')}")
                    # Once authenticated, request asset list
                    ws.send('42["getAssets", {}]')
                    print("[SEND] Requested assets list from PocketOption")

                elif event == "assets":
                    print("[RECV] Assets list received ✅")
                    assets = [
                        a["symbol"] for a in payload
                        if a.get("enabled") and a.get("type") == "forex"
                    ]
                    for asset in assets:
                        ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                    print(f"[SUBSCRIBE] Subscribed to {len(assets)} forex pairs 🔥")

                elif event == "ticks":
                    symbol = payload.get("asset")
                    price = payload.get("price")
                    tick_time = datetime.utcfromtimestamp(
                        payload["time"]
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[TICK] {symbol}: {price} at {tick_time}")

                    tick_data = {"symbol": symbol, "price": price, "time": tick_time}
                    if socketio:
                        socketio.emit("new_tick", tick_data)

                else:
                    print("[DEBUG] Unhandled event:", event, payload)

            except Exception as e:
                print("[ERROR decoding event]", e)

        else:
            # Unknown control message
            print(f"[CTRL/OTHER] {message}")

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
