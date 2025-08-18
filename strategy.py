import numpy as np
import pandas as pd

# ===============================
# Utility & Indicator Functions
# ===============================

def smma(series: pd.Series, length: int) -> pd.Series:
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
    low_min = df["low"].rolling(window=k).min()
    high_max = df["high"].rolling(window=k).max()
    k_raw = (df["close"] - low_min) / (high_max - low_min + 1e-9) * 100.0
    k_smooth = k_raw.rolling(window=smooth).mean()
    d_line = k_smooth.rolling(window=d).mean()
    return k_smooth, d_line

def fractal_high(df: pd.DataFrame):
    highs = df["high"]
    is_fractal = (highs.shift(0) > highs.shift(1)) & (highs.shift(0) > highs.shift(2)) & \
                 (highs.shift(0) > highs.shift(-1)) & (highs.shift(0) > highs.shift(-2))
    return is_fractal.fillna(False)

def fractal_low(df: pd.DataFrame):
    lows = df["low"]
    is_fractal = (lows.shift(0) < lows.shift(1)) & (lows.shift(0) < lows.shift(2)) & \
                 (lows.shift(0) < lows.shift(-1)) & (lows.shift(0) < lows.shift(-2))
    return is_fractal.fillna(False)

# ===============================
# Pocket Option Data Adapter
# ===============================

def format_pocket_option_candles(candles: list) -> pd.DataFrame:
    """
    Convert Pocket Option raw JSON candles into DataFrame.
    candles = [
      {"time": 1690800000, "open": 1.1234, "high": 1.1250, "low": 1.1220, "close": 1.1240},
      ...
    ]
    """
    df = pd.DataFrame(candles)
    df["time"] = pd.to_datetime(df["time"], unit="s")   # convert unix seconds → datetime
    df.set_index("time", inplace=True)
    df = df[["open", "high", "low", "close"]]           # enforce order
    return df

# ===============================
# Indicator Preparation
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

# ===============================
# Example Strategies
# ===============================

def evaluate_trend_reversal(df: pd.DataFrame):
    """
    Example: Simple oversold/overbought check with Stochastic.
    """
    last = df.iloc[-1]
    if last["%K"] < 20 and last["%D"] < 20:
        return "CALL"   # Buy
    elif last["%K"] > 80 and last["%D"] > 80:
        return "PUT"    # Sell
    return None

def evaluate_trend_following(df: pd.DataFrame):
    """
    Example: EMA trend following.
    """
    last = df.iloc[-1]
    if last["close"] > last["ema150"]:
        return "CALL"
    elif last["close"] < last["ema150"]:
        return "PUT"
    return None

# ===============================
# Entry Point for Runner
# ===============================

def check_signal(df: pd.DataFrame):
    """
    Main entry point for strategy_runner.py.
    Runs indicators + strategies and returns a signal.
    """
    if len(df) < 200:
        return None  # need enough candles

    df = prepare_indicators(df)

    # You can stack multiple strategies here
    signal = evaluate_trend_reversal(df)
    if signal:
        return signal

    signal = evaluate_trend_following(df)
    if signal:
        return signal

    return None
