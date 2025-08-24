# data_fetcher.py
import json
import time
import websocket
import threading
from collections import defaultdict
from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from config import TELEGRAM_CHAT_IDS
import pandas as pd
from datetime import datetime

# Store incoming data for all assets and timeframes
market_data = defaultdict(lambda: {"ticks": [], "candles": defaultdict(list)})

# Supported candle periods in seconds
CANDLE_PERIODS = [60, 120, 180, 300]  # 1m, 2m, 3m, 5m

# Store OTC symbols dynamically
otc_symbols = []

POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# Keep track of last heartbeat time
last_heartbeat = 0

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
    global otc_symbols
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None

            if event == "assets":
                print("[RECV] Assets list received ")
                # Filter only OTC currency pairs
                otc_symbols = [a["symbol"] for a in payload if a.get("enabled") and a.get("type")=="currency_pair" and a.get("category")=="OTC"]
                print(f"[DEBUG] OTC symbols: {otc_symbols[:5]} ... ({len(otc_symbols)} total)")

                # Prefill historical candles for each OTC symbol
                for asset in otc_symbols:
                    for period in CANDLE_PERIODS:
                        try:
                            ws.send(f'42["requestHistoricalCandles",{{"asset":"{asset}","period":{period},"count":50}}]')
                        except Exception as e:
                            print(f"[HIST PREFILL ERROR] {asset} {period}: {e}")

                # Subscribe to live ticks and candles for OTC symbols
                for asset in otc_symbols:
                    ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                    for period in CANDLE_PERIODS:
                        ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":{period}}}]')
                print(f"[SUBSCRIBE] Subscribed to {len(otc_symbols)} OTC assets 🔥")

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

def tf_to_seconds(tf):
    """Convert string timeframe (1m, 2m, 3m, 5m) to seconds"""
    return int(tf[:-1]) * 60

# --- Updated start_fetching with dynamic OTC symbols and no live candle wait ---
def start_fetching(symbols,timeframes, socketio, latest_signals):
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("Started start_fetching thread for dashboard & Telegram alerts.")

    TIMEFRAME_MAP = {"1m": 60, "2m": 120, "3m": 180, "5m": 300}

    while True:
        for symbol in otc_symbols:  # Use dynamic OTC symbol list
            for tf in timeframes:
                try:
                    period_seconds = TIMEFRAME_MAP.get(tf)
                    if not period_seconds:
                        logging.warning(f"[WARN] Timeframe {tf} not recognized.")
                        continue

                    candles = market_data[symbol]["candles"].get(period_seconds, [])
                    logging.debug(f"[DEBUG] {symbol} {tf}: {len(candles)} candles available")

                    # Remove the 30 live candle wait; signals start immediately if data exists
                    if not candles:
                        logging.info(f"[WAIT] No candles yet for {symbol} {tf}")
                        continue

                    df = pd.DataFrame(candles)
                    signal = analyze_candles(df)
                    if not signal:
                        logging.info(f"[NO SIGNAL] {symbol} {tf}")
                        continue

                    signal_data = {
                        "symbol": symbol,
                        "signal": signal,
                        "timeframe": tf,
                        "time": datetime.utcnow().strftime("%H:%M:%S")
                    }

                    latest_signals.append(signal_data)
                    if len(latest_signals) > 50:
                        latest_signals.pop(0)

                    socketio.emit("update_signal", signal_data)
                    logging.info(f"[SIGNAL] Emitted to dashboard: {symbol} {tf} → {signal}")

                    # Send Telegram alert
                    for chat_id in TELEGRAM_CHAT_IDS:
                        if chat_id:
                            try:
                                send_telegram_message(chat_id, f"{symbol} {tf} signal: {signal}")
                            except Exception as e:
                                logging.error(f"[TELEGRAM ERROR] {e}")

                except Exception as e:
                    logging.error(f"[ERROR processing {symbol} {tf}] {e}")

        logging.info(f"Latest signals count: {len(latest_signals)}")
        time.sleep(1)  # Prevent tight loop

if __name__ == "__main__":
    run_ws()
