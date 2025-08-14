import numpy as np
import pandas as pd

# ===============================
# Utility & Indicator Functions
# ===============================

def smma(series: pd.Series, length: int) -> pd.Series:
    """
    Williams' SMMA (Smoothed Moving Average) used for Alligator.
    SMMA_t = (SMMA_{t-1} * (length - 1) + price_t) / length
    """
    smma_vals = []
    prev = np.nan
    for i, val in enumerate(series):
        if i == 0:
            prev = val
        else:
            prev = (prev * (length - 1) + val) / length
        smma_vals.append(prev)
    return pd.Series(smma_vals, index=series.index)

def alligator(df: pd.DataFrame, jaw=15, teeth=8, lips=5):
    """
    Return Alligator lines (Jaw, Teeth, Lips) using SMMA on median price.
    """
    median = (df["high"] + df["low"]) / 2.0
    jaw_line = smma(median, jaw)
    teeth_line = smma(median, teeth)
    lips_line = smma(median, lips)
    return jaw_line, teeth_line, lips_line

def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()

def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = np.maximum.reduce([
        (high - low).values,
        (high - prev_close).abs().values,
        (low - prev_close).abs().values
    ])
    tr = pd.Series(tr, index=df.index)
    return tr.rolling(length).mean()

def stochastic_oscillator(df: pd.DataFrame, k=14, d=3, smooth=3):
    """
    Returns %K and %D.
    """
    low_min = df["low"].rolling(window=k).min()
    high_max = df["high"].rolling(window=k).max()
    k_raw = (df["close"] - low_min) / (high_max - low_min + 1e-9) * 100.0
    k_smooth = k_raw.rolling(window=smooth).mean()
    d_line = k_smooth.rolling(window=d).mean()
    return k_smooth, d_line

def fractal_high(df: pd.DataFrame, lookback=2, lookforward=2):
    """
    Bill Williams style: High greater than highs around it.
    Marks True where bar is a local swing high.
    """
    highs = df["high"]
    is_fractal = (highs.shift(0) > highs.shift(1)) & (highs.shift(0) > highs.shift(2)) & \
                 (highs.shift(0) > highs.shift(-1)) & (highs.shift(0) > highs.shift(-2))
    return is_fractal.fillna(False)

def fractal_low(df: pd.DataFrame, lookback=2, lookforward=2):
    lows = df["low"]
    is_fractal = (lows.shift(0) < lows.shift(1)) & (lows.shift(0) < lows.shift(2)) & \
                 (lows.shift(0) < lows.shift(-1)) & (lows.shift(0) < lows.shift(-2))
    return is_fractal.fillna(False)

def median_of_series(s: pd.Series, window: int):
    return s.rolling(window).median()

# ===============================
# Price Action Helpers
# ===============================

def candle_body(df, i):
    return abs(df.loc[i, "close"] - df.loc[i, "open"])

def candle_range(df, i):
    return df.loc[i, "high"] - df.loc[i, "low"]

def is_small_body(df, i, atr_series, factor=0.4):
    # Small body relative to ATR
    if i < 1:
        return False
    avg_atr = atr_series.iloc[i]
    return candle_body(df, i) <= factor * (avg_atr if not np.isnan(avg_atr) else candle_range(df, i))

def is_strong_bullish(df, i, atr_series, factor=0.6):
    # Large body, close near high, green candle
    if i < 1:
        return False
    body = df.loc[i, "close"] - df.loc[i, "open"]
    if body <= 0:
        return False
    rng = candle_range(df, i)
    avg_atr = atr_series.iloc[i]
    return body >= factor * (avg_atr if not np.isnan(avg_atr) else rng)

def is_strong_bearish(df, i, atr_series, factor=0.6):
    if i < 1:
        return False
    body = df.loc[i, "open"] - df.loc[i, "close"]
    if body <= 0:
        return False
    rng = candle_range(df, i)
    avg_atr = atr_series.iloc[i]
    return body >= factor * (avg_atr if not np.isnan(avg_atr) else rng)

def ema_slope(series: pd.Series, window=5):
    # simple slope: current EMA vs EMA n bars ago
    if len(series) < window + 1:
        return 0.0
    return series.iloc[-1] - series.iloc[-1 - window]

def lines_contracting(jaw, teeth, lips, lookback=5):
    """
    Alligator contraction: distances between lines reduced over last N bars.
    """
    d1_now = (lips.iloc[-1] - teeth.iloc[-1]).abs()
    d2_now = (teeth.iloc[-1] - jaw.iloc[-1]).abs()
    d1_prev = (lips.iloc[-1 - lookback] - teeth.iloc[-1 - lookback]).abs() if len(lips) > lookback else d1_now
    d2_prev = (teeth.iloc[-1 - lookback] - jaw.iloc[-1 - lookback]).abs() if len(jaw) > lookback else d2_now
    return (d1_now < d1_prev) and (d2_now < d2_prev)

def lines_crossing(jaw, teeth, lips):
    """
    Detect any crossing among the last few bars.
    """
    recent = 3
    lj = lips.iloc[-recent:]
    tt = teeth.iloc[-recent:]
    jw = jaw.iloc[-recent:]
    # if ordering changed recently
    def order(a, b, c):
        return (a > b) and (b > c)
    bullish_now = (lj.iloc[-1] > tt.iloc[-1] > jw.iloc[-1])
    bearish_now = (lj.iloc[-1] < tt.iloc[-1] < jw.iloc[-1])
    bullish_prev = order(lj.iloc[0], tt.iloc[0], jw.iloc[0])
    bearish_prev = order(-lj.iloc[0], -tt.iloc[0], -jw.iloc[0])
    return (bullish_now != bullish_prev) or (bearish_now != bearish_prev)

def near_level(price, level, tolerance):
    return abs(price - level) <= tolerance

# ===============================
# Core Evaluators
# ===============================

def prepare_indicators(df: pd.DataFrame):
    df = df.copy()
    df["ema150"] = ema(df["close"], 150)
    df["atr14"] = atr(df, 14)
    df["atr_median50"] = df["atr14"].rolling(50).median()
    df["%K"], df["%D"] = stochastic_oscillator(df, 14, 3, 3)
    df["fr_high"] = fractal_high(df)
    df["fr_low"] = fractal_low(df)
    df["jaw"], df["teeth"], df["lips"] = alligator(df, jaw=15, teeth=8, lips=5)
    return df

def historical_bias_reversal_zone(df: pd.DataFrame, lookback=50, touches_required=2):
    """
    Check whether price zone around last swing (fractal) has reversed price >= touches_required times.
    Approximation: count fractal lows/highs within a tolerance around recent level.
    """
    if len(df) < lookback + 5:
        return False
    recent = df.iloc[-lookback:]
    tol = recent["atr14"].iloc[-1] if not np.isnan(recent["atr14"].iloc[-1]) else (recent["high"] - recent["low"]).mean()
    price_now = recent["close"].iloc[-1]

    lows_levels = recent.loc[recent["fr_low"], "low"]
    highs_levels = recent.loc[recent["fr_high"], "high"]

    low_hits = (lows_levels.apply(lambda lv: near_level(price_now, lv, tol))).sum()
    high_hits = (highs_levels.apply(lambda hv: near_level(price_now, hv, tol))).sum()

    return (low_hits >= touches_required) or (high_hits >= touches_required)

def three_candle_reversal_pattern_buy(df: pd.DataFrame):
    i2 = len(df) - 1  # candle 3 index
    i1 = i2 - 1       # candle 2
    i0 = i2 - 2       # candle 1
    if i0 < 0:
        return False
    # C1: strong bear into support
    cond1 = (df.loc[i0, "close"] < df.loc[i0, "open"])  # red
    # Small body indecision on C2
    cond2 = is_small_body(df, i1, df["atr14"])
    # C3 strong bullish closing > high of C2
    cond3 = is_strong_bullish(df, i2, df["atr14"]) and (df.loc[i2, "close"] > df.loc[i1, "high"])
    return cond1 and cond2 and cond3

def three_candle_reversal_pattern_sell(df: pd.DataFrame):
    i2 = len(df) - 1
    i1 = i2 - 1
    i0 = i2 - 2
    if i0 < 0:
        return False
    cond1 = (df.loc[i0, "close"] > df.loc[i0, "open"])
    cond2 = is_small_body(df, i1, df["atr14"])
    cond3 = is_strong_bearish(df, i2, df["atr14"]) and (df.loc[i2, "close"] < df.loc[i1, "low"])
    return cond1 and cond2 and cond3

def evaluate_trend_reversal_5m(df: pd.DataFrame) -> dict:
    """
    Returns {'BUY': bool, 'SELL': bool}
    """
    signal = {"BUY": False, "SELL": False}
    if len(df) < 160:  # need enough for EMA150/ATR50
        return signal

    df = prepare_indicators(df)

    # Volatility filter
    vol_ok = (df["atr14"].iloc[-1] > df["atr_median50"].iloc[-1])
    if not vol_ok:
        return signal

    # Alligator exhaustion: contraction or crossing
    gator_contract = lines_contracting(df["jaw"], df["teeth"], df["lips"], lookback=5) or \
                     lines_crossing(df["jaw"], df["teeth"], df["lips"])

    # Historical bias
    hist_ok = historical_bias_reversal_zone(df, lookback=50, touches_required=2)

    # Stochastic
    k = df["%K"].iloc[-1]
    k_prev = df["%K"].iloc[-2] if len(df) >= 2 else k

    price = df["close"].iloc[-1]
    ema150_now = df["ema150"].iloc[-1]

    # --- BUY context ---
    buy_context = (price < ema150_now) and gator_contract and hist_ok and (k_prev < 20 and k > k_prev)
    buy_pattern = three_candle_reversal_pattern_buy(df)
    if buy_context and buy_pattern:
        signal["BUY"] = True

    # --- SELL context ---
    sell_context = (price > ema150_now) and gator_contract and hist_ok and (k_prev > 80 and k < k_prev)
    sell_pattern = three_candle_reversal_pattern_sell(df)
    if sell_context and sell_pattern:
        signal["SELL"] = True

    return signal

def three_candle_trend_follow_confirm_buy(df: pd.DataFrame):
    i2 = len(df) - 1
    i1 = i2 - 1
    i0 = i2 - 2
    if i0 < 0:
        return False
    # Pullback bearish bar above EMA150
    cond1 = (df.loc[i0, "close"] < df.loc[i0, "open"]) and (df.loc[i0, "close"] > df["ema150"].iloc[i0])
    # Indecision near lips
    cond2 = is_small_body(df, i1, df["atr14"])
    # Breakout strong bullish
    cond3 = is_strong_bullish(df, i2, df["atr14"]) and (df.loc[i2, "close"] > df.loc[i1, "high"])
    return cond1 and cond2 and cond3

def three_candle_trend_follow_confirm_sell(df: pd.DataFrame):
    i2 = len(df) - 1
    i1 = i2 - 1
    i0 = i2 - 2
    if i0 < 0:
        return False
    cond1 = (df.loc[i0, "close"] > df.loc[i0, "open"]) and (df.loc[i0, "close"] < df["ema150"].iloc[i0])
    cond2 = is_small_body(df, i1, df["atr14"])
    cond3 = is_strong_bearish(df, i2, df["atr14"]) and (df.loc[i2, "close"] < df.loc[i1, "low"])
    return cond1 and cond2 and cond3

def evaluate_trend_following(df: pd.DataFrame) -> dict:
    """
    For 1m/2m/3m.
    Returns {'BUY': bool, 'SELL': bool}
    """
    signal = {"BUY": False, "SELL": False}
    if len(df) < 160:
        return signal

    df = prepare_indicators(df)

    # Filters
    ema_s = ema_slope(df["ema150"], window=5)
    k = df["%K"].iloc[-1]
    k_prev = df["%K"].iloc[-2] if len(df) >= 2 else k
    atr_ok = df["atr14"].iloc[-1] > 0.5 * df["atr_median50"].iloc[-1] if not np.isnan(df["atr_median50"].iloc[-1]) else True

    price = df["close"].iloc[-1]
    ema_now = df["ema150"].iloc[-1]

    # Alligator alignment
    lips, teeth, jaw = df["lips"], df["teeth"], df["jaw"]
    bull_align = lips.iloc[-1] > teeth.iloc[-1] > jaw.iloc[-1]
    bear_align = lips.iloc[-1] < teeth.iloc[-1] < jaw.iloc[-1]

    # BUY trend-follow
    buy_ctx = (ema_s > 0) and (price > ema_now) and bull_align and atr_ok and (k_prev <= 40 and k > k_prev)
    buy_conf = three_candle_trend_follow_confirm_buy(df)
    if buy_ctx and buy_conf:
        signal["BUY"] = True

    # SELL trend-follow
    sell_ctx = (ema_s < 0) and (price < ema_now) and bear_align and atr_ok and (k_prev >= 60 and k < k_prev)
    sell_conf = three_candle_trend_follow_confirm_sell(df)
    if sell_ctx and sell_conf:
        signal["SELL"] = True

    return signal
