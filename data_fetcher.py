import json
import time
import websocket
import threading
from collections import defaultdict
from credentials import sessionToken, uid, ACCOUNT_URL
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from config import TELEGRAM_CHAT_IDS
import pandas as pd
from datetime import datetime, timezone

# Store incoming data for all assets and timeframes
market_data = defaultdict(lambda: {"ticks": [], "candles": defaultdict(list)})

# Supported candle periods in seconds
CANDLE_PERIODS = [60, 180, 300]  # 1m, 3m, 5m

PO_WS_URL = "wss://events-po.com/socket.io/?EIO=4&transport=websocket"

# Keep track of last heartbeat time
last_heartbeat = 0

# Dynamically loaded symbols from Pocket Option
symbols = []


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
    print("[OPEN] Connected to PocketOption WebSocket")
    # Step 1: Send namespace open (40)
    ws.send("40")
    print("[SEND] Namespace open (40) ✅")
    # Heartbeat thread will start after auth is sent


def on_message(ws, message):
    global symbols

    # Debug raw message
    logging.debug(f"[RAW MESSAGE] {message}")

    # Socket.IO heartbeat
    if message == "3":
        return

    # Step 2: After namespace confirmation, send probe (41)
    if message == "40":
        time.sleep(0.5)  # 500ms delay
        ws.send("41")
        print("[SEND] Probe (41) ✅")
        return

    # Step 3: After probe acknowledged, send staged auth (42)
    if message == "41":
        time.sleep(0.5)
        auth_payload = [
            "auth",
            {
                "sessionToken": sessionToken,
                "uid": uid,
                "lang": "en",
                "currentUrl": "cabinet/demo-quick-high-low",
                "isChart": 1
            }
        ]
        ws.send("42" + json.dumps(auth_payload))
        print("[SEND] Auth message sent ✅")
        return

    # Step 4: Handle server events
    if message.startswith("42"):
        try:
            payload = json.loads(message[2:])
            event, data = payload[0], payload[1] if len(payload) > 1 else None

            if event == "assets" and data:
                print("[EVENT] Assets list received")
                symbols = [a["symbol"] for a in data if a.get("enabled")]
                print(f"[DEBUG] {len(symbols)} enabled assets loaded")

                # Start subscriptions after assets confirmed
                for asset in symbols:
                    ws.send(f'42["subscribe",{{"type":"ticks","asset":"{asset}"}}]')
                    for period in CANDLE_PERIODS:
                        ws.send(f'42["subscribe",{{"type":"candles","asset":"{asset}","period":{period}}}]')
                print(f"[SUBSCRIBE] Subscribed to {len(symbols)} assets 🔥")

                # Start heartbeat AFTER subscriptions
                threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

            elif event == "ticks" and data:
                asset = data["asset"]
                tick = {"time": data["time"], "price": data["price"]}
                market_data[asset]["ticks"].append(tick)

            elif event == "candles" and data:
                asset = data["asset"]
                period = data["period"]
                candle = {
                    "time": data["time"],
                    "open": data["open"],
                    "high": data["high"],
                    "low": data["low"],
                    "close": data["close"],
                    "volume": data["volume"],
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
                PO_WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_close=on_close,
                on_error=on_error,
                header=["Origin: https://m.pocketoption.com"]
            )

            threading.Thread(target=send_heartbeat, args=(ws), daemon=True).start()
            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)


def get_market_data():
    return market_data


def get_dynamic_symbols():
    """
    Return the latest dynamically loaded symbols.
    Waits until at least one symbol is loaded.
    """
    global symbols
    wait_time = 0
    while not symbols and wait_time < 10:
        time.sleep(0.5)
        wait_time += 0.5
    return symbols.copy()


def start_fetching(timeframes, socketio, latest_signals):
    """
    Continuously fetch Pocket Option candles for dynamic symbols & timeframes,
    analyze signals, update latest_signals list, and emit to dashboard via socketio.
    """
    while True:
        current_symbols = get_dynamic_symbols()
        for symbol in current_symbols:
            for tf in timeframes:
                candles = market_data[symbol]["candles"].get(tf_to_seconds(tf), [])
                if not candles:
                    continue
                df = pd.DataFrame(candles)
                result = analyze_candles(df)

                if isinstance(result, tuple):
                    signal_value, confidence = result
                else:
                    signal_value = result
                    confidence = 100  # fallback default

                signal_data = {
                    "symbol": symbol,
                    "signal": signal_value if signal_value else "HOLD",
                    "confidence": confidence,
                    "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "timeframe": tf
                }

                # Update latest_signals list for dashboard
                latest_signals[:] = [s for s in latest_signals if not (s["symbol"] == symbol and s["timeframe"] == tf)]
                latest_signals.append(signal_data)

                # Emit live update to frontend
                socketio.emit("new_signal", signal_data)

                # Send Telegram alert only if there is a BUY/SELL signal
                if signal_value in ["BUY", "SELL"]:
                    for chat_id in TELEGRAM_CHAT_IDS:
                        if chat_id:
                            try:
                                send_telegram_message(chat_id, f"{symbol} {tf} signal: {signal_value} ({confidence}%)")
                            except Exception as e:
                                print("[TELEGRAM ERROR]", e)

        time.sleep(5)


def tf_to_seconds(tf):
    return int(tf[:-1]) * 60


if __name__ == "__main__":
    run_ws()
