# strategy_runner.py
"""
Strategy Runner
---------------
- Connects to Pocket Option WebSocket via PocketOptionWS
- Feeds live candlestick data into strategy.py
- Evaluates strategies on each new candle
- Prints (or later sends) signals in real time
"""

import asyncio
import json
import pandas as pd
from datetime import datetime

from pocket_option import PocketOptionWS
import strategy  # your existing strategy.py file with logic

# Symbols & Timeframes to monitor
SYMBOLS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc"]
TIMEFRAME = 60  # seconds (1 minute candles)

# Store candle history for each symbol
candles_data = {symbol: [] for symbol in SYMBOLS}

def process_candle(symbol, candle):
    """Handle new candle and run strategy."""
    # Append to local history
    candles_data[symbol].append(candle)
    
    # Keep only the last 100 candles
    if len(candles_data[symbol]) > 100:
        candles_data[symbol] = candles_data[symbol][-100:]

    # Convert to DataFrame
    df = pd.DataFrame(candles_data[symbol])
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Run strategy (must be implemented in strategy.py)
    signal = strategy.check_signal(df)

    if signal:
        print(f"[{datetime.utcnow()}] {symbol} - SIGNAL: {signal}")

async def on_candle(symbol, data):
    """Callback when a new candle is received."""
    try:
        candle = {
            "time": data["time"],
            "open": float(data["open"]),
            "close": float(data["close"]),
            "high": float(data["high"]),
            "low": float(data["low"]),
            "volume": float(data.get("volume", 0))
        }
        process_candle(symbol, candle)
    except Exception as e:
        print(f"Error processing candle for {symbol}: {e}")

async def main():
    ws = PocketOptionWS()

    # Connect WebSocket
    await ws.connect()

    # Subscribe to candles for each symbol
    for symbol in SYMBOLS:
        await ws.subscribe_candles(symbol, TIMEFRAME, lambda data, s=symbol: asyncio.create_task(on_candle(s, data)))

    # Keep alive
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")
