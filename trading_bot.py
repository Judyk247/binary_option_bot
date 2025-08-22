# trading_bot.py
import asyncio
from data_fetcher import get_market_data, connect_pocket
from datetime import datetime, timedelta

# Import strategy functions (EMA, Alligator, Stochastic, etc.)
from strategy import (
    calculate_ema,
    calculate_alligator,
    calculate_stochastic,
    check_price_action_patterns,
    calculate_atr
)

# Timeframes in seconds
TIMEFRAMES = [60, 120, 180, 300]  # 1m, 2m, 3m, 5m

# Minimum number of candles to analyze
HISTORICAL_CANDLES = 50

# Volatility filter threshold (ATR)
ATR_THRESHOLD = 0.0005  # adjust per asset

async def analyze_candles(asset, candles):
    """
    Analyze historical candles with full strategy:
    - EMA-150 trend
    - Alligator trend
    - Stochastic (overbought/oversold)
    - Price action pattern detection
    - Volatility filter
    """
    signals = []

    if len(candles) < HISTORICAL_CANDLES:
        return signals

    recent_candles = candles[-HISTORICAL_CANDLES:]

    # Extract OHLC
    opens = [c["open"] for c in recent_candles]
    highs = [c["high"] for c in recent_candles]
    lows = [c["low"] for c in recent_candles]
    closes = [c["close"] for c in recent_candles]

    # EMA Trend
    ema = calculate_ema(closes, period=150)

    # Alligator
    jaw, teeth, lips = calculate_alligator(highs, lows, closes)

    # Stochastic
    stochastic_k, stochastic_d = calculate_stochastic(highs, lows, closes, k_period=14, d_period=3)

    # ATR Volatility
    atr = calculate_atr(highs, lows, closes, period=14)
    if atr < ATR_THRESHOLD:
        return signals  # skip low-volatility setups

    # Price action patterns
    pa_signal = check_price_action_patterns(recent_candles)

    # Strategy Conditions (simplified for clarity)
    last_close = closes[-1]

    # Buy Conditions
    if (last_close > ema[-1] and last_close > jaw[-1] and last_close > teeth[-1] and last_close > lips[-1]
        and stochastic_k[-1] < 30 and pa_signal == "bull"):
        signals.append({"asset": asset, "type": "BUY", "time": datetime.utcnow()})

    # Sell Conditions
    if (last_close < ema[-1] and last_close < jaw[-1] and last_close < teeth[-1] and last_close < lips[-1]
        and stochastic_k[-1] > 80 and pa_signal == "bear"):
        signals.append({"asset": asset, "type": "SELL", "time": datetime.utcnow()})

    return signals

async def signal_loop():
    """
    Main loop to scan all assets continuously across all timeframes.
    """
    while True:
        market_snapshot = get_market_data()

        for asset, data in market_snapshot.items():
            for period in TIMEFRAMES:
                candles = data["candles"].get(period, [])
                signals = await analyze_candles(asset, candles)

                for signal in signals:
                    print(f"[SIGNAL] {signal['type']} {signal['asset']} | {period}s | {signal['time']}")

        # Update dashboard every 1min
        await asyncio.sleep(60)

async def main():
    # Run WebSocket connection and signal analysis concurrently
    await asyncio.gather(
        connect_pocket(),
        signal_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
