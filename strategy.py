import numpy as np
import pandas as pd

def calculate_ema(prices, period):
    """Calculate EMA for a list of prices"""
    emas = []
    k = 2 / (period + 1)
    for i, price in enumerate(prices):
        if i == 0:
            emas.append(price)
        else:
            ema = price * k + emas[-1] * (1 - k)
            emas.append(ema)
    return emas

def heikin_ashi(df):
    """Convert OHLC to Heikin Ashi candles"""
    ha_df = df.copy()
    ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
    ha_df.iloc[0, ha_df.columns.get_loc('open')] = df['open'].iloc[0]
    ha_df['high'] = ha_df[['open', 'close', 'high']].max(axis=1)
    ha_df['low'] = ha_df[['open', 'close', 'low']].min(axis=1)
    return ha_df

def calculate_atr(df, period=14):
    """Average True Range"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift(1))
    low_close = np.abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def calculate_alligator(df, jaw=13, teeth=8, lips=5):
    """Alligator lines using SMAs of median price"""
    median_price = (df['high'] + df['low']) / 2
    jaw_line = median_price.rolling(jaw).mean()
    teeth_line = median_price.rolling(teeth).mean()
    lips_line = median_price.rolling(lips).mean()
    return jaw_line, teeth_line, lips_line

def stochastic_oscillator(df, k_period=14, d_period=3):
    """Stochastic %K and %D"""
    low_min = df['low'].rolling(k_period).min()
    high_max = df['high'].rolling(k_period).max()
    k = 100 * (df['close'] - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d

def detect_bullish_engulfing(df):
    if len(df) < 2:
        return False
    prev, last = df.iloc[-2], df.iloc[-1]
    return last['close'] > last['open'] and prev['close'] < prev['open'] \
           and last['close'] > prev['open'] and last['open'] < prev['close']

def detect_bearish_engulfing(df):
    if len(df) < 2:
        return False
    prev, last = df.iloc[-2], df.iloc[-1]
    return last['close'] < last['open'] and prev['close'] > prev['open'] \
           and last['open'] > prev['close'] and last['close'] < prev['open']

def analyze_candles(df):
    """Return 'buy', 'sell', or None signal"""
    if len(df) < 30:
        return None

    ha_df = heikin_ashi(df)
    atr = calculate_atr(df)
    jaw, teeth, lips = calculate_alligator(ha_df)
    k, d = stochastic_oscillator(ha_df)
    ema = ha_df['close'].ewm(span=150, adjust=False).mean()

    last_idx = -1
    recent = ha_df.iloc[-30:]
    bullish_bias = recent['close'].mean() > recent['open'].mean()
    bearish_bias = recent['close'].mean() < recent['open'].mean()
    bullish_pattern = detect_bullish_engulfing(recent)
    bearish_pattern = detect_bearish_engulfing(recent)

    is_buy = (
        ha_df['close'].iloc[last_idx] > jaw.iloc[last_idx] and
        ha_df['close'].iloc[last_idx] > teeth.iloc[last_idx] and
        ha_df['close'].iloc[last_idx] > lips.iloc[last_idx] and
        k.iloc[last_idx] > d.iloc[last_idx] and
        k.iloc[last_idx] < 30 and
        bullish_bias and
        bullish_pattern and
        atr.iloc[last_idx] > 0
    )

    is_sell = (
        ha_df['close'].iloc[last_idx] < jaw.iloc[last_idx] and
        ha_df['close'].iloc[last_idx] < teeth.iloc[last_idx] and
        ha_df['close'].iloc[last_idx] < lips.iloc[last_idx] and
        k.iloc[last_idx] < d.iloc[last_idx] and
        k.iloc[last_idx] > 80 and
        bearish_bias and
        bearish_pattern and
        atr.iloc[last_idx] > 0
    )

    if is_buy:
        return "buy"
    elif is_sell:
        return "sell"
    else:
        return None
