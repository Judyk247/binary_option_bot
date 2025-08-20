import os
import json
import time
import threading
import websocket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PO_EMAIL = os.getenv("PO_EMAIL")
PO_PASSWORD = os.getenv("PO_PASSWORD")
PO_API_BASE = os.getenv("PO_API_BASE")  # Now contains IP-based WS URL

class PocketOptionFetcher:
    def __init__(self, symbols, timeframes):
        self.symbols = symbols
        self.timeframes = timeframes
        self.ws = None
        self.candles_data = {sym: {tf: [] for tf in timeframes} for sym in symbols}
        self.connected = False
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while True:
            try:
                self._connect()
            except Exception as e:
                print(f"[PocketOptionFetcher] Connection error: {e}")
            time.sleep(5)  # Reconnect delay

    def _connect(self):
        def on_open(ws):
            print("[PocketOptionFetcher] WebSocket opened.")
            self.connected = True
            self._login(ws)

        def on_message(ws, message):
            data = json.loads(message)
            # Example: store candle data
            if "candles" in data:
                symbol = data.get("symbol")
                timeframe = data.get("timeframe")
                if symbol and timeframe:
                    self.candles_data[symbol][timeframe] = data["candles"]

        def on_error(ws, error):
            print(f"[PocketOptionFetcher] WebSocket error: {error}")

        def on_close(ws, close_status_code, close_msg):
            print(f"[PocketOptionFetcher] WebSocket closed: {close_status_code}, {close_msg}")
            self.connected = False

        self.ws = websocket.WebSocketApp(
            PO_API_BASE,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        self.ws.run_forever()

    def _login(self, ws):
        login_payload = {
            "action": "login",
            "email": PO_EMAIL,
            "password": PO_PASSWORD
        }
        ws.send(json.dumps(login_payload))
        print("[PocketOptionFetcher] Login request sent.")

    def get_candles(self, symbol, timeframe):
        # Return the latest candles for a symbol + timeframe
        return self.candles_data.get(symbol, {}).get(timeframe, [])
