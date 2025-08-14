# config.py
# Project-wide configuration (non-secrets). Secrets are read from environment variables (.env).

import os

# -----------------------
# Secrets (must be set in .env or environment)
# -----------------------
# Put your Twelve Data API key in your .env as TWELVE_DATA_API_KEY
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")  # REQUIRED

# Optional override for cache TTL (seconds). Default = 300 (5 minutes)
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

# -----------------------
# Timeframes to scan (use short names used across the app)
# -----------------------
TIMEFRAMES = ["1m", "2m", "3m", "5m"]

# -----------------------
# SYMBOL LIST (60 currency pairs)
# -----------------------
SYMBOLS = [
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

# -----------------------
# Strategy constants
# -----------------------
EMA_PERIOD = 150

# Stochastic thresholds
STOCH_OVERBOUGHT = 80
STOCH_OVERSOLD = 20

# Alligator (per your spec)
ALLIGATOR_JAW = 15
ALLIGATOR_TEETH = 8
ALLIGATOR_LIPS = 5

# ATR / historical bias windows
ATR_PERIOD = 14
ATR_MEDIAN_WINDOW = 50
HISTORICAL_LOOKBACK_5M = 50

# Minimum candles required to evaluate signals (ensures EMA150 + ATR median available)
MIN_CANDLES_REQUIRED = 160

# Data fetch default outputsize (number of candles requested from Twelve Data)
DEFAULT_OUTPUTSIZE = 300
