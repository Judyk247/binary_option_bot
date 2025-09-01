import json
import time
import websocket
import threading
from collections import defaultdict
from credentials import sessionToken, uid, ACCOUNT_URL
from strategy import analyze_candles  # Your EMA/Stochastic/Alligator logic
from telegram_utils import send_telegram_message  # Telegram alert function
from config import TELEGRAM_CHAT_IDS, SYMBOLS, TIMEFRAMES
import pandas as pd
from datetime import datetime, timezone

# --- Initialize market data for all symbols and timeframes ---
market_data = defaultdict(lambda: {"ticks": [], "candles": defaultdict(list)})
for symbol in SYMBOLS:
    for tf in TIMEFRAMES:
        market_data[symbol]["candles"][tf] = []

# --- Supported candle periods in seconds ---
CANDLE_PERIODS = [60, 120, 180, 300]  # 1m, 2m, 3m, 5m
POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# --- Heartbeat to keep WS alive ---
last_heartbeat = 0
def send_heartbeat(ws):
    global last_heartbeat
    while True:
        try:
            ws.send("2")  # Socket.IO ping
            last_heartbeat = time.time()
        except Exception as e:
            print("[HEARTBEAT ERROR]", e)
        time.sleep(5)

# --- WebSocket event handlers ---
def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")
    # Authenticate
    auth_msg = f'42["auth",{{"sessionToken":"{sessionToken}","uid":"{uid}","lang":"en","currentUrl":"cabinet","isChart":1}}]'
    ws.send(auth_msg)
    print("[SEND] Auth message sent")

    # Subscribe to ticks and candles dynamically from SYMBOLS
    for asset in SYMBOLS:
        ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
        for period in CANDLE_PERIODS:
            ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":{period}}}]')
    print(f"[SUBSCRIBE] Subscribed to {len(SYMBOLS)} assets 🔥")

def on_message(ws, message):
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None

            if event == "ticks" and payload:
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
                # Convert period seconds back to string timeframe
                tf = f"{period // 60}m"
                market_data[asset]["candles"][tf].append(candle)

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
            threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()
            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)

# --- Utility functions ---
def tf_to_seconds(tf):
    """Convert string timeframe (1m, 3m, 5m) to seconds"""
    return int(tf[:-1]) * 60

def get_market_data():
    """Return the latest market data snapshot"""
    return market_data

# --- Live fetching and signal analysis for dashboard ---
def start_fetching(symbols, timeframes, socketio, latest_signals):
    """
    Continuously fetch Pocket Option candles for symbols & timeframes,
    analyze signals, update latest_signals, and emit to dashboard.
    """
    while True:
        for symbol in symbols:
            for tf in timeframes:
                candles = market_data[symbol]["candles"].get(tf, [])
                if not candles:
                    print(f"[DEBUG] No candles yet for {symbol} {tf}")
                    continue

                df = pd.DataFrame(candles)
                result = analyze_candles(df)

                if isinstance(result, tuple):
                    signal_value, confidence = result
                else:
                    signal_value = result
                    confidence = 100

                signal_data = {
                    "symbol": symbol,
                    "signal": signal_value if signal_value else "HOLD",
                    "confidence": confidence,
                    "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "timeframe": tf
                }

                print(f"[DEBUG] {signal_data['time']} | {symbol} {tf} -> Signal: {signal_data['signal']} | Confidence: {signal_data['confidence']}%")

                # Update latest_signals for dashboard
                latest_signals[:] = [s for s in latest_signals if not (s["symbol"] == symbol and s["timeframe"] == tf)]
                latest_signals.append(signal_data)
                socketio.emit("new_signal", signal_data)
                print(f"[DEBUG] Emitted signal to dashboard: {symbol} {tf}")

                # Send Telegram alert for BUY/SELL
                if signal_value in ["BUY", "SELL"]:
                    for chat_id in TELEGRAM_CHAT_IDS:
                        if chat_id:
                            try:
                                send_telegram_message(chat_id, f"{symbol} {tf} signal: {signal_value} ({confidence}%)")
                                print(f"[DEBUG] Telegram alert sent to {chat_id}: {signal_value} ({confidence}%)")
                            except Exception as e:
                                print("[TELEGRAM ERROR]", e)

        time.sleep(5)

if __name__ == "__main__":
    run_ws()
