# data_fetcher.py
"""
Module to fetch live market data from Pocket Option.
Handles websocket connection, reconnection, and streaming
candlestick data for multiple timeframes.
"""

import json
import threading
import websocket
import time
from collections import defaultdict

# ------------------------------
# Top-level function for app.py
# ------------------------------
_fetcher_instances = {}

def get_live_data(symbols, timeframes):
    """
    Returns a dictionary of live candle data for given symbols and timeframes.
    Example output: {
        'EURUSD_1m': [...],
        'EURUSD_2m': [...],
        'GBPUSD_3m': [...],
        'USDJPY_5m': [...]
    }
    """
    global _fetcher_instances

    # Create a unique key for this set of symbols+timeframes
    key = "_".join(symbols) + "_" + "_".join(timeframes)

    # Start fetcher if not already running
    if key not in _fetcher_instances:
        fetcher = PocketOptionFetcher(symbols, timeframes)
        fetcher.start()
        _fetcher_instances[key] = fetcher

    # Collect latest candles
    data = {}
    fetcher = _fetcher_instances[key]
    for symbol in symbols:
        for tf in timeframes:
            data_key = f"{symbol}_{tf}"
            data[data_key] = fetcher.get_candles(symbol, tf)

    return data
    
class PocketOptionFetcher:
    def __init__(self, pairs, timeframes):
        self.pairs = pairs
        self.timeframes = timeframes
        self.ws = None
        self.data = defaultdict(list)  # stores candles per symbol+timeframe
        self.keep_running = True
        self.lock = threading.Lock()

    def _on_message(self, ws, message):
        try:
            msg = json.loads(message)
            if "candle" in msg:
                symbol = msg["candle"]["symbol"]
                tf = str(msg["candle"]["tf"])
                candle = {
                    "time": msg["candle"]["time"],
                    "open": float(msg["candle"]["open"]),
                    "high": float(msg["candle"]["high"]),
                    "low": float(msg["candle"]["low"]),
                    "close": float(msg["candle"]["close"])
                }
                key = f"{symbol}_{tf}"
                with self.lock:
                    self.data[key].append(candle)
                    # keep last 100 candles
                    if len(self.data[key]) > 100:
                        self.data[key] = self.data[key][-100:]
        except Exception as e:
            print("Error parsing message:", e)

    def _on_error(self, ws, error):
        print("WebSocket error:", error)

    def _on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed:", close_status_code, close_msg)
        # attempt reconnect
        if self.keep_running:
            time.sleep(5)
            self._connect()

    def _on_open(self, ws):
        print("WebSocket connection established.")
        # subscribe to chosen pairs and timeframes
        for symbol in self.pairs:
            for tf in self.timeframes:
                sub_msg = {
                    "event": "subscribe",
                    "symbol": symbol,
                    "tf": tf
                }
                ws.send(json.dumps(sub_msg))

    def _connect(self):
        url = "wss://ws.pocketoption.com/echo"  # pocket option ws endpoint
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        wst = threading.Thread(target=self.ws.run_forever, daemon=True)
        wst.start()

    def start(self):
        self.keep_running = True
        self._connect()

    def stop(self):
        self.keep_running = False
        if self.ws:
            self.ws.close()

    def get_candles(self, symbol, timeframe):
        """
        Returns latest candle data for symbol+timeframe.
        """
        key = f"{symbol}_{timeframe}"
        with self.lock:
            return list(self.data.get(key, []))
