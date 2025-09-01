import json
import time
import websocket
from datetime import datetime
from threading import Thread
from config import SYMBOLS, market_data, TIMEFRAMES, DEBUG

# Flask socketio instance will be injected from app.py
socketio = None  

# Pocket Option WebSocket URL
POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# Credentials
from credentials import uid, sessionToken, ACCOUNT_URL

def send_keepalive(ws):
    """Send periodic ping to keep WebSocket alive."""
    while True:
        try:
            ws.send("2")  # Engine.IO ping
            if DEBUG:
                print("[PING] Keep-alive sent")
        except Exception as e:
            print("[PING ERROR]", e)
            break
        time.sleep(20)  # ping every 20s

def on_open(ws):
    if DEBUG:
        print("[OPEN] Connected to Pocket Option WebSocket")

    # Open default namespace
    ws.send("40")
    time.sleep(1)

    # Send auth message
    auth_payload = [
        "auth",
        {
            "sessionToken": sessionToken,
            "uid": uid,
            "lang": "en",
            "currentUrl": "cabinet",
            "isChart": 1
        }
    ]
    ws.send(f'42["auth",{json.dumps(auth_payload)}]')
    time.sleep(1)

    # Request assets list
    ws.send('42["getAssets", {}]')

    # Start keepalive ping
    Thread(target=send_keepalive, args=(ws,), daemon=True).start()

def on_message(ws, message):
    global socketio

    try:
        if not message.startswith("42"):
            return

        data = json.loads(message[2:])
        event = data[0]
        payload = data[1] if len(data) > 1 else None

        if DEBUG:
            print("[WS MESSAGE]", event, payload)

        # --- Populate SYMBOLS dynamically ---
        if event == "assets" and payload:
            SYMBOLS.clear()
            for asset in payload:
                symbol_id = asset.get("symbol")
                if symbol_id:
                    SYMBOLS.append(symbol_id)
                    # Initialize market_data for new symbols
                    market_data[symbol_id]["candles"] = {tf: [] for tf in TIMEFRAMES}
                    market_data[symbol_id]["ticks"] = []

            if DEBUG:
                print(f"[INFO] Loaded symbols dynamically: {SYMBOLS}")

            # Subscribe to ticks and candles
            for symbol in SYMBOLS:
                ws.send(f'42["subscribe",{{"type":"ticks","asset":"{symbol}"}}]')
                for tf in TIMEFRAMES:
                    period_sec = int(tf[:-1]) * 60
                    ws.send(f'42["subscribe",{{"type":"candles","asset":"{symbol}","period":{period_sec}}}]')
            if DEBUG:
                print(f"[SUBSCRIBE] Subscribed to {len(SYMBOLS)} symbols 🔥")

        # --- Update ticks ---
        elif event == "ticks" and payload:
            symbol = payload.get("asset")
            price = payload.get("price")
            tick_time = datetime.utcfromtimestamp(payload["time"]).strftime("%Y-%m-%d %H:%M:%S")

            if symbol not in market_data:
                market_data[symbol] = {"ticks": [], "candles": {tf: [] for tf in TIMEFRAMES}}

            market_data[symbol]["ticks"].append({"price": price, "time": tick_time})

            # Emit tick to dashboard
            if socketio:
                socketio.emit("new_tick", {"symbol": symbol, "price": price, "time": tick_time})

        # --- Update candles ---
        elif event == "candles" and payload:
            symbol = payload.get("asset")
            period_sec = payload.get("period")
            tf = f"{period_sec // 60}m"
            candle = payload.get("candle")

            if symbol and tf and candle:
                market_data[symbol]["candles"][tf].append(candle)
                # Keep only last 50 candles
                if len(market_data[symbol]["candles"][tf]) > 50:
                    market_data[symbol]["candles"][tf].pop(0)

    except Exception as e:
        print("[WS ERROR parsing message]", e)

def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] Connection closed:", close_status_code, close_msg)

def on_error(ws, error):
    print("[ERROR]", error)

def run_ws():
    """Main WebSocket loop with auto-reconnect."""
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
            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)

def start_pocket_ws(sio):
    """Start Pocket Option WS in background from app.py."""
    global socketio
    socketio = sio
    Thread(target=run_ws, daemon=True).start()

if __name__ == "__main__":
    print("⚠️ Run this only from app.py, not directly.")
