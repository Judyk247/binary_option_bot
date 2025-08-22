import asyncio
import json
import websockets
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import telegram
from credentials import (
    POCKET_SESSION_TOKEN,
    POCKET_USER_ID,
    POCKET_ACCOUNT_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)

# Telegram bot setup
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# WebSocket URL
POCKET_WS_URL = "wss://ws.pocketoption.com/socket.io/?EIO=3&transport=websocket"

# Settings
TIMEFRAMES = [60, 120, 180, 300]  # 1m, 2m, 3m, 5m in seconds
CANDLE_HISTORY = 50               # Number of candles to analyze
ATR_PERIOD = 14                   # ATR period for volatility filter
VOLATILITY_THRESHOLD = 0.0005     # Min ATR to consider valid signal

# In-memory candle storage
candles_data = {}  # {symbol: {timeframe: [candles]}}


def compute_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def compute_atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr


def detect_candlestick_patterns(df):
    patterns = []
    for i in range(1, len(df)):
        open_ = df['open'].iloc[i]
        close = df['close'].iloc[i]
        prev_open = df['open'].iloc[i - 1]
        prev_close = df['close'].iloc[i - 1]
        # Bullish engulfing
        if close > open_ and prev_close < prev_open and close > prev_open and open_ < prev_close:
            patterns.append('bullish_engulfing')
        # Bearish engulfing
        elif close < open_ and prev_close > prev_open and close < prev_open and open_ > prev_close:
            patterns.append('bearish_engulfing')
        else:
            patterns.append(None)
    patterns.insert(0, None)
    df['pattern'] = patterns
    return df


def analyze_candles(df):
    if len(df) < CANDLE_HISTORY:
        return None
    df = detect_candlestick_patterns(df)
    df['ema150'] = compute_ema(df['close'], 150)
    atr = compute_atr(df, ATR_PERIOD).iloc[-1]
    if atr < VOLATILITY_THRESHOLD:
        return None  # Skip low volatility
    last_candle = df.iloc[-1]
    signal = None
    if last_candle['close'] > last_candle['ema150']:
        if last_candle['pattern'] == 'bullish_engulfing':
            signal = 'BUY'
    elif last_candle['close'] < last_candle['ema150']:
        if last_candle['pattern'] == 'bearish_engulfing':
            signal = 'SELL'
    return signal


async def send_telegram_alert(symbol, signal, timeframe):
    msg = f"Signal: {signal}\nSymbol: {symbol}\nTimeframe: {timeframe // 60}min\nTime: {datetime.utcnow()}"
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)


async def subscribe_assets(ws):
    await ws.send(json.dumps([42, ["getAssets", {}]]))


async def handle_message(ws, message):
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None
            if event == "assets":
                for asset in payload:
                    if asset.get("enabled"):
                        symbol = asset['symbol']
                        candles_data[symbol] = {tf: [] for tf in TIMEFRAMES}
                        for tf in TIMEFRAMES:
                            await ws.send(json.dumps([42, ["subscribe", {"type": "candles", "asset": symbol, "period": tf}]]))
                            await ws.send(json.dumps([42, ["subscribe", {"type": "ticks", "asset": symbol}]]))
                        print(f"[SUBSCRIBE] {symbol} ✅")
            elif event == "candles":
                symbol = payload['asset']
                timeframe = payload['period']
                candle = {
                    'open': payload['open'],
                    'high': payload['high'],
                    'low': payload['low'],
                    'close': payload['close'],
                    'time': payload['time']
                }
                candles_data[symbol][timeframe].append(candle)
                # Keep last CANDLE_HISTORY
                if len(candles_data[symbol][timeframe]) > CANDLE_HISTORY:
                    candles_data[symbol][timeframe] = candles_data[symbol][timeframe][-CANDLE_HISTORY:]
                df = pd.DataFrame(candles_data[symbol][timeframe])
                signal = analyze_candles(df)
                if signal:
                    # Send alert 30s before next candle
                    asyncio.create_task(send_telegram_alert(symbol, signal, timeframe))
        except Exception as e:
            print("[ERROR parsing]", e)


async def connect_pocket():
    while True:
        try:
            async with websockets.connect(POCKET_WS_URL) as ws:
                # Auth
                auth_msg = [42, ["auth", {
                    "sessionToken": POCKET_SESSION_TOKEN,
                    "uid": POCKET_USER_ID,
                    "lang": "en",
                    "currentUrl": POCKET_ACCOUNT_URL,
                    "isChart": 1
                }]]
                await ws.send(json.dumps(auth_msg))
                print(f"✅ Connected to Pocket Option ({POCKET_ACCOUNT_URL})")

                await subscribe_assets(ws)

                while True:
                    message = await ws.recv()
                    await handle_message(ws, message)
        except Exception as e:
            print("❌ Connection error:", e)
            print("🔄 Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(connect_pocket())
