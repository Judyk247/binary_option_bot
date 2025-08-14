import os
import time
import requests
import pandas as pd

# === CONFIG ===
TWELVE_DATA_API_KEY = "c1516b63b0e54828bc83861b9676501f"  # Provided by you
BASE_URL = "https://api.twelvedata.com/time_series"

# Reasonable default list (you can edit). Keep it moderate to respect API limits.
DEFAULT_SYMBOLS = [
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","USD/CAD","AUD/USD","NZD/USD",
    "EUR/GBP","EUR/JPY","EUR/CHF","EUR/AUD","EUR/CAD","EUR/NZD",
    "GBP/JPY","GBP/CHF","GBP/AUD","GBP/CAD","GBP/NZD",
    "AUD/JPY","AUD/CHF","AUD/CAD","AUD/NZD",
    "NZD/JPY","NZD/CHF","NZD/CAD",
    "CAD/JPY","CAD/CHF","CHF/JPY",
    "USD/TRY","EUR/TRY","USD/ZAR","EUR/ZAR","USD/MXN","EUR/MXN",
    "USD/SEK","EUR/SEK","USD/NOK","EUR/NOK","USD/DKK","EUR/DKK",
    "USD/SGD","EUR/SGD","USD/HKD",
    "USD/CNH","EUR/CNH","GBP/SGD","AUD/SGD","NZD/SGD","CHF/SGD","CAD/SGD",
    "GBP/SEK","GBP/NOK","GBP/DKK",
    "NOK/SEK","SEK/JPY","NOK/JPY","TRY/JPY","ZAR/JPY","MXN/JPY",
    "EUR/PLN"
]

# Twelve Data intervals mapping
VALID_INTERVALS = {"1m": "1min", "2m": "2min", "3m": "3min", "5m": "5min"}

def fetch_candles(symbol: str, interval: str, outputsize: int = 200) -> pd.DataFrame:
    """
    Fetch OHLCV for one symbol + interval.
    Returns a DataFrame in ascending time order with columns: open, high, low, close, volume, datetime (pd.DatetimeIndex).
    """
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Unsupported interval: {interval}")

    params = {
        "symbol": symbol,
        "interval": VALID_INTERVALS[interval],
        "apikey": TWELVE_DATA_API_KEY,
        "outputsize": outputsize,
        "format": "JSON",
        "order": "ASC",
    }

    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if "values" not in data:
        # Handle error payloads gracefully
        raise RuntimeError(f"Twelve Data error for {symbol} {interval}: {data}")

    df = pd.DataFrame(data["values"])
    # Ensure numeric dtypes
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Datetime and sort
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df[["datetime", "open", "high", "low", "close", "volume"]]
    return df


def fetch_batch(symbols, intervals=("1m", "2m", "3m", "5m"), outputsize=200):
    """
    Fetch candles for many symbols and intervals.
    Returns nested dict: data[symbol][interval] = DataFrame
    """
    data = {}
    for sym in symbols:
        data[sym] = {}
        for itv in intervals:
            try:
                df = fetch_candles(sym, itv, outputsize=outputsize)
                data[sym][itv] = df
                # Gentle pacing to respect free tier
                time.sleep(0.15)
            except Exception as e:
                # In case of a failure, keep empty to avoid breaking dashboard
                data[sym][itv] = pd.DataFrame()
    return data
