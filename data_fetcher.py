import json
import time
import websocket
import threading
from collections import defaultdict
from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL
from strategy import analyze_candles
from telegram_utils import send_telegram_message
import pandas as pd
from datetime import datetime

# --- Global market data storage ---
market_data = defaultdict(lambda: {"candles": defaultdict(list)})

POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"


# --- WebSocket run loop ---
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


def get_market_data():
    return market_data


def tf_to_seconds(tf):
    return int(tf[:-1]) * 60


# --- Historical candles fetcher (WebSocket-based) ---
def fetch_historical_candles(symbol, period_seconds, count):
    """
    Fetch historical OTC candles from Pocket Option via WebSocket.
    Returns a list of dicts.
    """
    candles = []
    try:
        WS_URL = POCKET_WS_URL
        done = threading.Event()

        def on_open(ws):
            auth_msg = f'42["auth",{{"sessionToken":"{POCKET_SESSION_TOKEN}","uid":"{POCKET_USER_ID}","lang":"en","currentUrl":"{POCKET_ACCOUNT_URL}","isChart":1}}]'
            ws.send(auth_msg)
            ws.send(f'42["get_candles",{{"asset":"{symbol}","period":{period_seconds},"count":{count}}}]')

        def on_message(ws, message):
            nonlocal candles
            if message.startswith("42"):
                try:
                    data = json.loads(message[2:])
                    event = data[0]
                    payload = data[1] if len(data) > 1 else None

                    if event == "candles" and payload and payload.get("asset") == symbol and payload.get("period") == period_seconds:
                        for c in payload["candles"]:
                            candle = {
                                "time": c["time"],
                                "open": c["open"],
                                "high": c["high"],
                                "low": c["low"],
                                "close": c["close"],
                                "volume": c.get("volume", 0)
                            }
                            candles.append(candle)
                        done.set()
                except Exception as e:
                    print(f"[HISTORICAL ERROR] {symbol} {period_seconds}: {e}")
                    done.set()

        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=lambda ws, err: done.set(),
            on_close=lambda ws, code, msg: done.set(),
            header=["Origin: https://m.pocketoption.com"]
        )

        wst = threading.Thread(target=ws.run_forever, daemon=True)
        wst.start()
        done.wait(timeout=5)
        ws.close()
        wst.join(timeout=1)

    except Exception as e:
        print(f"[FETCH HISTORICAL ERROR] {symbol} {period_seconds}: {e}")

    return candles[-count:] if candles else []


# --- Threaded Pre-fill historical candles ---
def prefill_historical_candles(symbols, timeframes, fetch_historical_fn):
    TIMEFRAME_MAP = {"1m": 60, "2m": 120, "3m": 180, "5m": 300}

    def fetch_for_symbol(symbol):
        for tf in timeframes:
            period_seconds = TIMEFRAME_MAP.get(tf)
            if not period_seconds:
                continue
            try:
                candles = fetch_historical_fn(symbol, period_seconds, 50)
                if candles:
                    market_data[symbol]["candles"][period_seconds] = candles[-50:]
                    print(f"[PREFILL] {symbol} {tf}: Loaded {len(candles)} historical candles")
            except Exception as e:
                print(f"[PREFILL ERROR] {symbol} {tf}: {e}")

    threads = []
    for symbol in symbols:
        t = threading.Thread(target=fetch_for_symbol, args=(symbol,), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


# --- Signal generator (immediate, no wait) ---
def start_fetching(symbols, timeframes, socketio, latest_signals):
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("Started start_fetching thread for dashboard & Telegram alerts.")

    TIMEFRAME_MAP = {"1m": 60, "2m": 120, "3m": 180, "5m": 300}

    while True:
        for symbol in symbols:  # Uses whatever symbols you pass (otc_symbols in app.py)
            for tf in timeframes:
                try:
                    period_seconds = TIMEFRAME_MAP.get(tf)
                    if not period_seconds:
                        continue

                    candles = market_data[symbol]["candles"].get(period_seconds, [])
                    if candles:
                        df = pd.DataFrame(candles)
                        signal = analyze_candles(df)
                        if signal:
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
                            logging.info(f"[SIGNAL] {symbol} {tf} → {signal}")

                            for chat_id in TELEGRAM_CHAT_IDS:
                                if chat_id:
                                    try:
                                        send_telegram_message(chat_id, f"{symbol} {tf} signal: {signal}")
                                    except Exception as e:
                                        logging.error(f"[TELEGRAM ERROR] {e}")

                except Exception as e:
                    logging.error(f"[ERROR processing {symbol} {tf}] {e}")

        logging.info(f"Latest signals count: {len(latest_signals)}")
        time.sleep(1)


if __name__ == "__main__":
    run_ws()
