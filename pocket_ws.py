import json
import time
import websocket
from datetime import datetime
from threading import Thread
from config import SYMBOLS, market_data, TIMEFRAMES, DEBUG
from credentials import uid, sessionToken, ACCOUNT_URL

# Flask socketio instance will be injected from app.py
socketio = None  

POCKET_WS_URL = "wss://events-po.com/socket.io/?EIO=4&transport=websocket"

def send_keepalive(ws):
    """Keep-alive ping loop (prevents server disconnect)."""
    while True:
        try:
            ws.send("2")  # Engine.IO ping
            if DEBUG:
                print("[PING] Keep-alive sent")
        except Exception as e:
            print("[PING ERROR]", e)
            break
        time.sleep(15)  # < pingInterval (25s) to stay alive

def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Step 1: open namespace
    ws.send("40")
    print("[SEND] Namespace open (40) ✅")

    # Start keepalive pings
    Thread(target=send_keepalive, args=(ws,), daemon=True).start()

def on_message(ws, message):
    global socketio
    try:
        print(f"[RAW MESSAGE] {message}")

        if message.startswith("0"):
            if DEBUG:
                print("[INFO] Engine.IO handshake received")
            return

        if message.startswith("40{"):
            if DEBUG:
                print("[INFO] Namespace confirmed:", message)

            # ✅ Send auth *after* namespace confirmation
            auth_payload = {
                "sessionToken": sessionToken,
                "uid": uid,
                "lang": "en",
                "currentUrl": ACCOUNT_URL,
                "isChart": 1
            }
            auth_msg = f'42["auth",{json.dumps(auth_payload)}]'
            ws.send(auth_msg)
            print("[SEND] auth message sent ✅")

            # Request assets after auth
            ws.send('42["getAssets", {}]')
            print("[SEND] Requested assets list")
            return

        if message == "40":
            if DEBUG:
                print("[INFO] Namespace opened (40)")
            return

        if not message.startswith("42"):
            return

        data = json.loads(message[2:])
        event = data[0]
        payload = data[1] if len(data) > 1 else None

        if DEBUG:
            print(f"[WS EVENT] {event} | Payload: {payload}")

        # --- Populate SYMBOLS dynamically ---
        if event == "assets" and payload:
            SYMBOLS.clear()
            for asset in payload:
                symbol_id = asset.get("symbol")
                if symbol_id:
                    SYMBOLS.append(symbol_id)
                    market_data[symbol_id]["candles"] = {tf: [] for tf in TIMEFRAMES}

            print(f"[INFO] Loaded symbols dynamically: {SYMBOLS}")

            # Subscribe after symbols are loaded
            for symbol in SYMBOLS:
                ws.send(f'42["subscribe",{{"type":"ticks","asset":"{symbol}"}}]')
                for tf in TIMEFRAMES:
                    period_sec = int(tf[:-1]) * 60
                    ws.send(f'42["subscribe",{{"type":"candles","asset":"{symbol}","period":{period_sec}}}]')
            print(f"[SUBSCRIBE] Subscribed to {len(SYMBOLS)} symbols 🔥")

        # --- Update ticks ---
        elif event == "ticks" and payload:
            symbol = payload.get("asset")
            price = payload.get("price")
            tick_time = datetime.utcfromtimestamp(payload["time"]).strftime("%Y-%m-%d %H:%M:%S")
            market_data[symbol]["ticks"] = market_data[symbol].get("ticks", [])
            market_data[symbol]["ticks"].append({"price": price, "time": tick_time})

            if socketio:
                socketio.emit("new_tick", {"symbol": symbol, "price": price, "time": tick_time})

        # --- Update candles ---
        elif event == "candles" and payload:
            symbol = payload.get("asset")
            period_sec = payload.get("period")
            tf = f"{period_sec//60}m"
            candle = payload.get("candle")
            if symbol and tf and candle:
                market_data[symbol]["candles"][tf].append(candle)
                if len(market_data[symbol]["candles"][tf]) > 50:
                    market_data[symbol]["candles"][tf].pop(0)

    except Exception as e:
        print("[WS ERROR parsing message]", e)

def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] Connection closed:", close_status_code, close_msg)

def on_error(ws, error):
    print("[ERROR]", error)

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
            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)

def start_pocket_ws(socketio, POCKET_WS_URL, sessionToken, uid, ACCOUNT_URL):
    """
    Starts the Pocket Option WebSocket in a separate thread.
    
    Args:
        socketio: SocketIO instance
        POCKET_WS_URL: Pocket Option WebSocket URL
        sessionToken: Pocket Option session token
        uid: Pocket Option user ID
        ACCOUNT_URL: Pocket Option account URL
    """
    # Start the WebSocket thread and pass all required arguments
    Thread(
        target=run_ws,
        args=(socketio, POCKET_WS_URL, sessionToken, uid, ACCOUNT_URL),
        daemon=True
    ).start()
if __name__ == "__main__":
    print("⚠️ Run this only from app.py, not directly.")
