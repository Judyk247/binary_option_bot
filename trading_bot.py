# trading_bot.py
import asyncio
import json
import pandas as pd
import websockets
from datetime import datetime, timedelta
from strategy import analyze_candles
from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import requests

POCKET_WS_URL = "wss://ws.pocketoption.com/echo"

# Timeframes in seconds
TIMEFRAMES = {
    "1m": 60,
    "2m": 120,
    "3m": 180,
    "5m": 300
}

# Data storage for candles
candles_data = {tf: {} for tf in TIMEFRAMES}  # symbol -> dataframe

# Telegram alert function
def send_telegram_alert(symbol, signal, timeframe):
    message = f"📈 Signal: {signal.upper()} | {symbol} | Timeframe: {timeframe} | Time: {datetime.utcnow()}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
    print("[TELEGRAM] Alert sent:", message)

async def subscribe_assets(ws):
    """Request assets list and subscribe to ticks + candles"""
    await ws.send(json.dumps([42, ["getAssets", {}]]))
    print("[SEND] Requested assets list")

async def handle_asset_event(ws, payload):
    for asset in payload:
        symbol = asset["symbol"]
        if not asset.get("enabled"):
            continue
        for period in TIMEFRAMES.values():
            msg = [42, ["subscribe", {"type": "candles", "asset": symbol, "period": period}]]
            await ws.send(json.dumps(msg))
        tick_msg = [42, ["subscribe", {"type": "ticks", "asset": symbol}]]
        await ws.send(json.dumps(tick_msg))
    print(f"[SUBSCRIBE] Subscribed to {len(payload)} assets")

async def process_candle(symbol, timeframe, candle):
    """Update local candle storage"""
    if symbol not in candles_data[timeframe]:
        candles_data[timeframe][symbol] = pd.DataFrame(columns=["open", "high", "low", "close"])
    df = candles_data[timeframe][symbol]
    new_row = {"open": candle["o"], "high": candle["h"], "low": candle["l"], "close": candle["c"]}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    if len(df) > 50:
        df = df.iloc[-50:]  # keep last 50 candles
    candles_data[timeframe][symbol] = df

    # Analyze for signal
    signal = analyze_candles(df)
    if signal:
        send_telegram_alert(symbol, signal, timeframe)

async def handle_message(ws, message):
    if message.startswith("42"):
        data = json.loads(message[2:])
        event, payload = data[0], data[1] if len(data) > 1 else None

        if event == "assets":
            await handle_asset_event(ws, payload)
        elif event == "candles":
            symbol = payload["asset"]
            period = payload["period"]
            tf = next((k for k,v in TIMEFRAMES.items() if v==period), None)
            if tf:
                await process_candle(symbol, tf, payload)

async def connect_pocket():
    while True:
        try:
            async with websockets.connect(POCKET_WS_URL) as ws:
                # Auth message
                auth_msg = [
                    42,
                    [
                        "auth",
                        {
                            "sessionToken": POCKET_SESSION_TOKEN,
                            "uid": POCKET_USER_ID,
                            "lang": "en",
                            "currentUrl": POCKET_ACCOUNT_URL,
                            "isChart": 1
                        },
                    ],
                ]
                await ws.send(json.dumps(auth_msg))
                print(f"[OPEN] Connected ✅ | {POCKET_ACCOUNT_URL}")

                await subscribe_assets(ws)

                while True:
                    message = await ws.recv()
                    await handle_message(ws, message)

        except Exception as e:
            print("[ERROR] WebSocket error:", e)
            print("🔄 Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(connect_pocket())
