import json
import time
import websocket
import threading
from collections import defaultdict
from credentials import SECRET, ID, ACCOUNT_URL
from strategy import analyze_candles  # Your EMA/Stochastic/Alligator logic
from telegram_utils import send_telegram_message  # Your Telegram alert function
from config import TELEGRAM_CHAT_IDS
import pandas as pd
from datetime import datetime, timezone

# Store incoming data for all assets and timeframes
market_data = defaultdict(lambda: {"ticks": [], "candles": defaultdict(list)})

# Supported candle periods in seconds
CANDLE_PERIODS = [60, 120, 180, 300]  # 1m, 2m, 3m, 5m

POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# Keep track of last heartbeat time
last_heartbeat = 0

# --- Hardcoded fallback: 30 most popular Forex pairs ---
DEFAULT_SYMBOLS = [
    "EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "USD/CHF OTC", "AUD/USD OTC", "NZD/USD OTC",
    "USD/CAD OTC", "EUR/GBP OTC", "EUR/JPY OTC", "GBP/JPY OTC", "AUD/JPY OTC", "NZD/JPY OTC",
    "EUR/AUD OTC", "EUR/NZD OTC", "EUR/CAD OTC", "EUR/CHF OTC", "GBP/AUD OTC", "GBP/NZD OTC",
    "GBP/CAD OTC", "GBP/CHF OTC", "AUD/NZD OTC", "AUD/CAD OTC", "AUD/CHF OTC", "NZD/CAD OTC",
    "NZD/CHF OTC", "CAD/CHF OTC", "CAD/JPY OTC", "CHF/JPY OTC", "EUR/SEK OTC", "EUR/NOK OTC",
    "USD/SEK OTC", "USD/NOK OTC", "AUD/SGD OTC", "GBP/SGD OTC", "EUR/SGD OTC", "USD/SGD OTC",
    "EUR/HUF OTC", "USD/HUF OTC", "EUR/PLN OTC", "USD/PLN OTC"
]

def send_heartbeat(ws):
    global last_heartbeat
    while True:
        try:
            ws.send("2")  # Standard WebSocket ping for Socket.IO
            last_heartbeat = time.time()
        except Exception as e:
            print("[HEARTBEAT ERROR]", e)
        time.sleep(5)

def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Authenticate
    auth_msg = f'42["auth",{{"sessionToken":"{POCKET_SESSION_TOKEN}","uid":"{POCKET_USER_ID}","lang":"en","currentUrl":"{POCKET_ACCOUNT_URL}","isChart":1}}]'
    ws.send(auth_msg)
    print("[SEND] Auth message sent ")

def on_message(ws, message):
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None

            if event == "assets":
                print("[RECV] Assets list received ")
                assets = [a["symbol"] for a in payload if a.get("enabled")]
                print(f"[DEBUG] Assets enabled: {assets[:5]} ... ({len(assets)} total)")

                # If no assets received, fall back to hardcoded list
                if not assets:
                    print("[FALLBACK] Using hardcoded default symbols")
                    assets = DEFAULT_SYMBOLS

                # Subscribe to ticks and candles
                for asset in assets:
                    ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                    for period in CANDLE_PERIODS:
                        ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":{period}}}]')
                print(f"[SUBSCRIBE] Subscribed to {len(assets)} assets 🔥")

            elif event == "ticks" and payload:
                asset = payload["asset"]
                tick = {"time": payload["time"], "price": payload["price"]}
                market_data[asset]["ticks"].append(tick)

            elif event == "candles" and payload:
                asset = payload["asset"]
                period = payload["period"]
                candle = {
                    "time": payload["time"],
                    "open": payload["open"],
                    "high": payload["high"],
                    "low": payload["low"],
                    "close": payload["close"],
                    "volume": payload["volume"],
                }
                market_data[asset]["candles"][period].append(candle)

        except Exception as e:
            print("[ERROR parsing message]", e)

def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] Connection closed:", close_status_code, close_msg)

def on_error(ws, error):
    print("[ERROR]", error)

def run_ws():
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

            # Start heartbeat in background
            threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)

def get_market_data():
    """Return the latest market data snapshot"""
    return market_data

# --- New function for Flask dashboard / Live mode ---
def start_fetching(symbols, timeframes, socketio, latest_signals):
    """
    Continuously fetch Pocket Option candles for symbols & timeframes,
    analyze signals, update latest_signals list, and emit to dashboard via socketio.
    """
    while True:
        for symbol in (symbols or DEFAULT_SYMBOLS):
            for tf in timeframes:
                candles = market_data[symbol]["candles"].get(tf_to_seconds(tf), [])
                if not candles:
                    continue
                df = pd.DataFrame(candles)
                # Run your strategy
                signal = analyze_candles(df)
                signal_data = {
                    "symbol": symbol,
                    "signal": signal if signal else "HOLD",
                    "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "timeframe": tf
                }

                # Update latest_signals list for dashboard
                latest_signals[:] = [s for s in latest_signals if not (s["symbol"] == symbol and s["timeframe"] == tf)]
                latest_signals.append(signal_data)

                # Emit live update to frontend
                socketio.emit("new_signal", signal_data)

                # Send Telegram alert only if there is a BUY/SELL signal
                if signal in ["BUY", "SELL"]:
                    for chat_id in TELEGRAM_CHAT_IDS:
                        if chat_id:
                            try:
                                send_telegram_message(chat_id, f"{symbol} {tf} signal: {signal}")
                            except Exception as e:
                                print("[TELEGRAM ERROR]", e)

        time.sleep(5)  # Check every 5 seconds

def tf_to_seconds(tf):
    """Convert string timeframe (1m, 2m, 3m, 5m) to seconds"""
    return int(tf[:-1]) * 60

if __name__ == "__main__":
    run_ws()
