# data_fetcher.py
import json
import time
import websocket
import threading
from collections import defaultdict
from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL
from strategy import analyze_candles  # Your EMA/Stochastic/Alligator logic
from telegram_utils import send_telegram_message  # Your Telegram alert function
from config import TELEGRAM_CHAT_IDS
import pandas as pd
from datetime import datetime

# Store incoming data for all assets and timeframes
market_data = defaultdict(lambda: {"ticks": [], "candles": defaultdict(list)})

# Supported candle periods in seconds
CANDLE_PERIODS = [60, 120, 180, 300]  # 1m, 2m, 3m, 5m

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
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None

            if event == "assets":
                print("[RECV] Assets list received ")
                assets = [a["symbol"] for a in payload if a.get("enabled")]
                print(f"[DEBUG] Assets enabled: {assets[:5]} ... ({len(assets)} total)")

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
                print(f"[TICK] {asset}: {tick}")

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
                print(f"[CANDLE] {asset} {period}s: close={candle['close']}")

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

# --- Pre-fill historical candles function ---
def prefill_historical_candles(symbols, timeframes, fetch_historical_fn):
    """
    Fetch and pre-fill at least 30 candles per symbol/timeframe using fetch_historical_fn(symbol, period, count).
    """
    TIMEFRAME_MAP = {"1m": 60, "2m": 120, "3m": 180, "5m": 300}
    for symbol in symbols:
        for tf in timeframes:
            period_seconds = TIMEFRAME_MAP.get(tf)
            if not period_seconds:
                continue
            try:
                candles = fetch_historical_fn(symbol, period_seconds, 50)  # Fetch last 50 candles
                if candles:
                    market_data[symbol]["candles"][period_seconds] = candles[-50:]
                    print(f"[PREFILL] {symbol} {tf}: Loaded {len(candles)} historical candles")
            except Exception as e:
                print(f"[PREFILL ERROR] {symbol} {tf}: {e}")

# --- Updated start_fetching with full logging and sanity check ---
def start_fetching(symbols, timeframes, socketio, latest_signals):
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("Started start_fetching thread for dashboard & Telegram alerts.")

    TIMEFRAME_MAP = {"1m": 60, "2m": 120, "3m": 180, "5m": 300}

    while True:
        for symbol in symbols:
            for tf in timeframes:
                try:
                    period_seconds = TIMEFRAME_MAP.get(tf)
                    if not period_seconds:
                        logging.warning(f"[WARN] Timeframe {tf} not recognized.")
                        continue

                    candles = market_data[symbol]["candles"].get(period_seconds, [])
                    logging.debug(f"[DEBUG] {symbol} {tf}: {len(candles)} candles available")

                    # Only run analysis if at least 30 candles exist
                    if len(candles) < 30:
                        logging.info(f"[WAIT] Not enough candles for {symbol} {tf} ({len(candles)}/30)")
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
