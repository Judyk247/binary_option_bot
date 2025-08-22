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
PO_API_BASE = os.getenv("PO_API_BASE")  # IP-based WS URL

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
            try:
                if not message:  # Empty or None
                    print("[PocketOptionFetcher] Empty message received, skipping")
                    return

                data = json.loads(message)

                if not isinstance(data, dict):  # Ensure parsed JSON is a dict
                    print(f"[PocketOptionFetcher] Unexpected data format: {data}")
                    return

                # Store candle data safely
                candles = data.get("candles")
                symbol = data.get("symbol")
                timeframe = data.get("timeframe")

                if candles and symbol in self.symbols and timeframe in self.timeframes:
                    self.candles_data[symbol][timeframe] = candles
                else:
                    # Debug log for unrecognized messages
                    print(f"[PocketOptionFetcher] Ignored message: {data}")

            except (json.JSONDecodeError, TypeError) as e:
                print(f"[PocketOptionFetcher] JSON parse error: {e}, message: {message}")
            except Exception as e:
                print(f"[PocketOptionFetcher] Unexpected error in on_message: {e}")

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

        # Disable SSL verification for IP-based WS
        self.ws.run_forever(sslopt={"cert_reqs": 0})

    def _login(self, ws):
        if not PO_EMAIL or not PO_PASSWORD:
            print("[PocketOptionFetcher] Missing PO_EMAIL or PO_PASSWORD in .env")
            return
        login_payload = {
            "action": "login",
            "email": PO_EMAIL,
            "password": PO_PASSWORD
        }
        ws.send(json.dumps(login_payload))
        print("[PocketOptionFetcher] Login request sent.")

    def get_candles(self, symbol, timeframe):
        # Safely return latest candles
        return self.candles_data.get(symbol, {}).get(timeframe) or []
