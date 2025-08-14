# signal_generator.py

import pandas as pd
import numpy as np

# ------------------------------
# Indicator Functions
# ------------------------------

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def alligator(df, jaw=15, teeth=8, lips=5):
    df['Jaw'] = df['close'].shift(jaw)
    df['Teeth'] = df['close'].shift(teeth)
    df['Lips'] = df['close'].shift(lips)
    return df

def stochastic(df, k_period=14, d_period=3):
    df['Lowest_Low'] = df['low'].rolling(window=k_period).min()
    df['Highest_High'] = df['high'].rolling(window=k_period).max()
    df['%K'] = ((df['close'] - df['Lowest_Low']) /
               (df['Highest_High'] - df['Lowest_Low'])) * 100
    df['%D'] = df['%K'].rolling(window=d_period).mean()
    return df

def fractals(df):
    df['Fractal_High'] = df['high'][(df['high'].shift(2) < df['high']) &
                                    (df['high'].shift(1) < df['high']) &
                                    (df['high'].shift(-1) < df['high']) &
                                    (df['high'].shift(-2) < df['high'])]
    df['Fractal_Low'] = df['low'][(df['low'].shift(2) > df['low']) &
                                  (df['low'].shift(1) > df['low']) &
                                  (df['low'].shift(-1) > df['low']) &
                                  (df['low'].shift(-2) > df['low'])]
    return df

def atr(df, period=14):
    df['H-L'] = df['high'] - df['low']
    df['H-Cp'] = abs(df['high'] - df['close'].shift(1))
    df['L-Cp'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-Cp', 'L-Cp']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()
    return df

# ------------------------------
# Signal Detection
# ------------------------------

def detect_signal(df, timeframe="5m", strategy="reversal"):
    """
    Detects buy/sell signals based on your rules.
    strategy = "reversal" or "trend"
    timeframe = "1m", "2m", "3m", "5m"
    """
    if len(df) < 50:
        return None

    # Apply indicators
    df['EMA150'] = ema(df['close'], 150)
    df = alligator(df)
    df = stochastic(df)
    df = fractals(df)
    df = atr(df)

    median_atr = df['ATR'].rolling(50).median().iloc[-1]
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # ----------- Trend Reversal Strategy -----------
    if strategy == "reversal":
        # BUY (Call)
        buy_condition = (
            last['close'] < last['EMA150'] and
            (pd.notna(df['Fractal_Low'].iloc[-3:]).any()) and
            last['%K'] > prev['%K'] and prev['%K'] < 20 and
            last['ATR'] > median_atr
        )

        # SELL (Put)
        sell_condition = (
            last['close'] > last['EMA150'] and
            (pd.notna(df['Fractal_High'].iloc[-3:]).any()) and
            last['%K'] < prev['%K'] and prev['%K'] > 80 and
            last['ATR'] > median_atr
        )

    # ----------- Trend Following Strategy -----------
    elif strategy == "trend":
        # BUY (Call)
        buy_condition = (
            last['EMA150'] > prev['EMA150'] and
            last['close'] > last['EMA150'] and
            last['Lips'] > last['Teeth'] > last['Jaw'] and
            prev['%K'] < 40 and last['%K'] > prev['%K'] and
            last['ATR'] > (0.5 * median_atr)
        )

        # SELL (Put)
        sell_condition = (
            last['EMA150'] < prev['EMA150'] and
            last['close'] < last['EMA150'] and
            last['Lips'] < last['Teeth'] < last['Jaw'] and
            prev['%K'] > 60 and last['%K'] < prev['%K'] and
            last['ATR'] > (0.5 * median_atr)
        )

    else:
        return None

    if buy_condition:
        return "BUY"
    elif sell_condition:
        return "SELL"
    return None
