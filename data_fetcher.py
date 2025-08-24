# data_fetcher.py
import json
import time
import threading
from collections import defaultdict

import pandas as pd
import websocket

from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL
from strategy import analyze_candles  # Your EMA/Stochastic/Alligator logic
from telegram_utils import send_telegram_message  # Your Telegram alert function
from config import TELEGRAM_CHAT_IDS

# Store incoming data for all assets and timeframes
# NOTE: Keep candles bucketed by PERIOD IN SECONDS to stay compatible with tf_to_seconds()
market_data = defaultdict(lambda: {"ticks": [], "candles": defaultdict(list)})

# Supported candle periods in seconds
CANDLE_PERIODS = [60, 120, 180, 300]  # 1m, 2m, 3m, 5m

POCKET_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# Keep track of last heartbeat time
last_heartbeat = 0

# SocketIO instance (set by start_fetching so we can emit to the dashboard)
socketio_instance = None


def tf_to_seconds(tf: str) -> int:
    """Convert timeframe string like '1m' to seconds (e.g., 60)."""
    return int(tf[:-1]) * 60


def seconds_to_tf(sec: int) -> str:
    """Convert seconds (e.g., 60) to timeframe string (e.g., '1m')."""
    return f"{int(sec // 60)}m"


def send_heartbeat(ws):
    """Engine.IO ping. Helps keep some proxies happy."""
    global last_heartbeat
    while True:
        try:
            ws.send("2")  # Engine.IO ping
            last_heartbeat = time.time()
        except Exception as e:
            print("[HEARTBEAT ERROR]", e)
        time.sleep(5)


def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")

    # Authenticate
    auth_msg = (
        f'42["auth",{{'
        f'"sessionToken":"{POCKET_SESSION_TOKEN}",'
        f'"uid":"{POCKET_USER_ID}",'
        f'"lang":"en",'
        f'"currentUrl":"{POCKET_ACCOUNT_URL}",'
        f'"isChart":1'
        f"}}]"
    )
    ws.send(auth_msg)
    print("[SEND] Auth message sent ✅")

    # IMPORTANT: Request assets list after auth so we can subscribe
    ws.send('42["getAssets", {}]')
    print("[SEND] Requested assets list")


def on_message(ws, message):
    if not message.startswith("42"):
        return

    try:
        data = json.loads(message[2:])
        event = data[0]
        payload = data[1] if len(data) > 1 else None

        if event == "assets":
            print("[RECV] Assets list received ✅")
            assets = [a["symbol"] for a in payload if a.get("enabled")]

            # Subscribe to ticks and candles
            for asset in assets:
                ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                for period in CANDLE_PERIODS:
                    ws.send(
                        f'42["subscribe",{{"type":"candles","asset":"{asset}","period":{period}}}]'
                    )
            print(f"[SUBSCRIBE] Subscribed to {len(assets)} assets 🔥")

        elif event == "ticks" and payload:
            asset = payload.get("asset")
            if not asset:
                return
            tick = {"time": payload.get("time"), "price": payload.get("price")}
            market_data[asset]["ticks"].append(tick)

        elif event == "candles" and payload:
            asset = payload.get("asset")
            period = payload.get("period")  # e.g., 60, 120, 180, 300
            if not asset or not period:
                return

            candle = {
                "time": payload.get("time"),
                "open": payload.get("open"),
                "high": payload.get("high"),
                "low": payload.get("low"),
                "close": payload.get("close"),
                "volume": payload.get("volume"),
            }
            # Keep storage by numeric seconds to stay compatible with tf_to_seconds()
            market_data[asset]["candles"][period].append(candle)

            # Build DF and analyze
            df = pd.DataFrame(market_data[asset]["candles"][period])
            if not df.empty:
                signal = analyze_candles(df)
            else:
                signal = None

            # If we have a signal, notify Telegram and dashboard immediately
            if signal:
                tf_str = seconds_to_tf(period)

                # Telegram
                for chat_id in TELEGRAM_CHAT_IDS:
                    if chat_id:
                        try:
                            send_telegram_message(chat_id, f"{asset} {tf_str} signal: {signal}")
                        except Exception as e:
                            print("[TELEGRAM ERROR]", e)

                # Dashboard emit
                if socketio_instance:
                    try:
                        socketio_instance.emit(
                            "new_signal",
                            {"symbol": asset, "timeframe": tf_str, "signal": signal},
                            broadcast=True,
                        )
                    except Exception as e:
                        print("[SOCKETIO EMIT ERROR]", e)

    except Exception as e:
        print("[ERROR parsing message]", e)


def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] Connection closed:", close_status_code, close_msg)


def on_error(ws, error):
    print("[ERROR]", error)


def run_ws():
    """Connect and auto-reconnect to the Pocket Option WS forever."""
    while True:
        try:
            ws = websocket.WebSocketApp(
                POCKET_WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_close=on_close,
                on_error=on_error,
                header=["Origin: https://m.pocketoption.com"],
            )

            # Heartbeat in the background
            threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)

        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)


def get_market_data():
    """Return the latest market data snapshot"""
    return market_data


# --- Public entry used by app.py ---
def start_fetching(symbols, timeframes, socketio):
    """
    Continuously keep the WS alive, analyze signals, and emit to the dashboard.
    NOTE:
      - Keeps storage by numeric seconds
      - Emits to dashboard using string timeframes ('1m', '2m', etc.)
    """
    global socketio_instance
    socketio_instance = socketio

    # Ensure WS is running
    threading.Thread(target=run_ws, daemon=True).start()

    # Periodic re-check / backfill for dashboard (even if WS already emitted)
    while True:
        try:
            for symbol in symbols:
                for tf in timeframes:
                    sec = tf_to_seconds(tf)
                    candles = market_data[symbol]["candles"].get(sec, [])
                    if not candles:
                        continue

                    df = pd.DataFrame(candles)
                    if df.empty:
                        continue

                    signal = analyze_candles(df)

                    # Emit to dashboard regardless (show "No Signal" too)
                    if socketio_instance:
                        try:
                            socketio_instance.emit(
                                "new_signal",
                                {"symbol": symbol, "timeframe": tf, "signal": signal or "No Signal"},
                                broadcast=True,
                            )
                        except Exception as e:
                            print("[SOCKETIO EMIT ERROR]", e)

                    # Telegram only for actual signals
                    if signal:
                        for chat_id in TELEGRAM_CHAT_IDS:
                            if chat_id:
                                try:
                                    send_telegram_message(chat_id, f"{symbol} {tf} signal: {signal}")
                                except Exception as e:
                                    print("[TELEGRAM ERROR]", e)

        except Exception as loop_err:
            print("[FETCH LOOP ERROR]", loop_err)

        time.sleep(30)


if __name__ == "__main__":
    run_ws()
