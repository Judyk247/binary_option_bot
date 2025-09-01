import os
import websocket
import threading
import json
from dotenv import load_dotenv
from collections import defaultdict
import time

# Load environment variables
load_dotenv()

# --- Pocket Option credentials ---
PO_EMAIL = os.getenv("PO_EMAIL")
PO_PASSWORD = os.getenv("PO_PASSWORD")

# --- WebSocket URL ---
PO_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")

# --- Timeframes ---
TIMEFRAMES = ["1m", "3m", "5m"]
CANDLE_PERIODS = {"1m": 60, "3m": 180, "5m": 300}

# --- Debug ---
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# --- Market data ---
market_data = defaultdict(lambda: {"candles": defaultdict(list)})

# --- Symbols loaded dynamically ---
SYMBOLS = []

# --- WebSocket heartbeat ---
def send_heartbeat(ws):
    while True:
        try:
            ws.send("2")
        except Exception as e:
            print("[HEARTBEAT ERROR]", e)
        time.sleep(5)

# --- WebSocket handlers ---
def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")
    ws.send('42["getAssets", {}]')  # Request asset list
    threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

def on_message(ws, message):
    if not message.startswith("42"):
        return

    try:
        data = json.loads(message[2:])
        event = data[0]
        payload = data[1] if len(data) > 1 else None

        if DEBUG:
            print("[WS MESSAGE]", event, payload)

        # --- Load symbols dynamically ---
        if event == "assets" and payload:
            SYMBOLS.clear()
            for asset in payload:
                symbol_id = asset.get("symbol")
                if symbol_id:
                    SYMBOLS.append(symbol_id)
                    # Initialize market_data for this symbol
                    market_data[symbol_id]["candles"] = defaultdict(list)
                    # Subscribe to candles automatically
                    for tf, period in CANDLE_PERIODS.items():
                        ws.send(f'42["subscribe",{{"type":"candles","asset":"{symbol_id}","period":{period}}}]')
            print(f"[INFO] Loaded symbols dynamically: {SYMBOLS}")

        # --- Update candles ---
        if event == "candles" and payload:
            symbol = payload.get("asset")
            period = payload.get("period")
            candle = payload
            if symbol and period and candle:
                # Map period back to timeframe string
                tf = next((k for k, v in CANDLE_PERIODS.items() if v == period), str(period))
                market_data[symbol]["candles"][tf].append(candle)
                # Keep last 50 candles
                if len(market_data[symbol]["candles"][tf]) > 50:
                    market_data[symbol]["candles"][tf].pop(0)

    except Exception as e:
        print("[WS ERROR parsing message]", e)

def on_close(ws, code, msg):
    print("[CLOSE] WebSocket closed:", code, msg)

def on_error(ws, error):
    print("[ERROR]", error)

def start_ws():
    while True:
        try:
            ws = websocket.WebSocketApp(
                PO_WS_URL,
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

# --- Auto-start if run standalone ---
if __name__ == "__main__":
    threading.Thread(target=start_ws, daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 WebSocket stopped")
