import numpy as np
import pandas as pd

def calculate_ema(prices, period):
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
    ha_df = df.copy()
    ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
    ha_df.iloc[0, ha_df.columns.get_loc('open')] = df['open'].iloc[0]
    ha_df['high'] = ha_df[['open', 'close', 'high']].max(axis=1)
    ha_df['low'] = ha_df[['open', 'close', 'low']].min(axis=1)
    return ha_df

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift(1))
    low_close = np.abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def calculate_alligator(df, jaw=13, teeth=8, lips=5):
    median_price = (df['high'] + df['low']) / 2
    jaw_line = median_price.rolling(jaw).mean()
    teeth_line = median_price.rolling(teeth).mean()
    lips_line = median_price.rolling(lips).mean()
    return jaw_line, teeth_line, lips_line

def stochastic_oscillator(df, k_period=14, d_period=3):
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

# --- Multi-Timeframe Confirmation ---
def multi_timeframe_confirmation(lower_signal, mid_df, high_df):
    """
    lower_signal = signal from 1m
    mid_df = 3m candles (must agree with 1m)
    high_df = 5m candles (filter, must not oppose)
    """
    if lower_signal is None:
        return None

    def get_bias(df):
        if df is None or len(df) < 50:
            return None, 0
        ha = heikin_ashi(df)
        ema = ha['close'].ewm(span=100, adjust=False).mean()
        ema_slope = ema.iloc[-1] - ema.iloc[-5]
        bullish = ha['close'].mean() > ha['open'].mean()
        bearish = ha['close'].mean() < ha['open'].mean()
        return ("bullish" if ema_slope > 0 and bullish else
                "bearish" if ema_slope < 0 and bearish else None), ema_slope

    mid_bias, _ = get_bias(mid_df)
    high_bias, _ = get_bias(high_df)

    # 1m Buy needs 3m bullish, and 5m not bearish
    if lower_signal == "buy" and mid_bias == "bullish" and high_bias != "bearish":
        return "buy"
    # 1m Sell needs 3m bearish, and 5m not bullish
    elif lower_signal == "sell" and mid_bias == "bearish" and high_bias != "bullish":
        return "sell"
    else:
        return None

def analyze_candles(df, mid_df=None, high_df=None, debug=False):
    if len(df) < 50:
        if debug:
            print("Not enough candles: have", len(df))
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

    ema_slope = ema.iloc[-1] - ema.iloc[-5]
    min_atr = atr.iloc[last_idx] > df['close'].mean() * 0.001
    last_candle = ha_df.iloc[last_idx]
    body = abs(last_candle['close'] - last_candle['open'])
    upper_wick = last_candle['high'] - max(last_candle['close'], last_candle['open'])
    lower_wick = min(last_candle['close'], last_candle['open']) - last_candle['low']

    momentum_bull = (ha_df['close'].iloc[-3:] > ha_df['open'].iloc[-3:]).sum() >= 2
    momentum_bear = (ha_df['close'].iloc[-3:] < ha_df['open'].iloc[-3:]).sum() >= 2

    is_buy = (
        ha_df['close'].iloc[last_idx] > jaw.iloc[last_idx] and
        ha_df['close'].iloc[last_idx] > teeth.iloc[last_idx] and
        ha_df['close'].iloc[last_idx] > lips.iloc[last_idx] and
        k.iloc[last_idx] > d.iloc[last_idx] and
        k.iloc[last_idx] < 30 and
        bullish_bias and bullish_pattern and
        atr.iloc[last_idx] > 0 and
        ema_slope > 0 and min_atr and
        momentum_bull and
        upper_wick < body * 0.5
    )

    is_sell = (
        ha_df['close'].iloc[last_idx] < jaw.iloc[last_idx] and
        ha_df['close'].iloc[last_idx] < teeth.iloc[last_idx] and
        ha_df['close'].iloc[last_idx] < lips.iloc[last_idx] and
        k.iloc[last_idx] < d.iloc[last_idx] and
        k.iloc[last_idx] > 80 and
        bearish_bias and bearish_pattern and
        atr.iloc[last_idx] > 0 and
        ema_slope < 0 and min_atr and
        momentum_bear and
        lower_wick < body * 0.5
    )

    raw_signal = "buy" if is_buy else "sell" if is_sell else None
    confirmed = multi_timeframe_confirmation(raw_signal, mid_df, high_df)

    if debug:
        print("--- Candle Analysis Debug ---")
        print("Raw Signal:", raw_signal, "Confirmed:", confirmed)

    return confirmed
