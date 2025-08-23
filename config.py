import os
import websocket
import threading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Pocket Option credentials ---
PO_EMAIL = os.getenv("PO_EMAIL")
PO_PASSWORD = os.getenv("PO_PASSWORD")

# --- Pocket Option WebSocket ---
PO_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# --- Telegram bot details ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")  # Supports multiple IDs

# --- Default trading symbols ---
SYMBOLS = [
    "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc",
    "USDCAD_otc", "USDCHF_otc", "EURGBP_otc", "EURJPY_otc",
    "GBPJPY_otc", "AUDJPY_otc"
]

# --- Timeframes for scanning ---
TIMEFRAMES = ["1m", "2m", "3m", "5m"]

# --- Debug mode ---
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# --- WebSocket handlers ---
def send_heartbeat(ws):
    """Send ping every 5 seconds to keep connection alive"""
    import time
    while True:
        try:
            ws.send("2")  # Socket.IO ping
        except Exception as e:
            print("[HEARTBEAT ERROR]", e)
        time.sleep(5)

def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")
    # Request asset list
    ws.send('42["getAssets", {}]')
    threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

def on_message(ws, message):
    if message.startswith("42"):
        import json
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None
            print("[WS MESSAGE]", event, payload)
        except Exception as e:
            print("[WS ERROR parsing message]", e)

def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] WebSocket closed:", close_status_code, close_msg)

def on_error(ws, error):
    print("[ERROR]", error)

def start_ws():
    """Start WebSocket connection with auto-reconnect"""
    import time
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

# --- Start WebSocket automatically if this config is run standalone ---
if __name__ == "__main__":
    threading.Thread(target=start_ws, daemon=True).start()
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 WebSocket stopped")
