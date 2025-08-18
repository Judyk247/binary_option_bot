# pocket_option.py
"""
Utility module to handle WebSocket connections to Pocket Option.
Responsible for:
- Connecting to Pocket Option WebSocket
- Subscribing to currency pairs
- Receiving live tick data
- Handling reconnections on disconnect
"""

import json
import websocket
import threading
import time

class PocketOptionWS:
    def __init__(self, url="wss://ws.pocketoption.com/", symbols=None, on_message=None):
        """
        :param url: Pocket Option WebSocket endpoint
        :param symbols: List of currency pairs (e.g., ["EURUSD_otc", "GBPUSD_otc"])
        :param on_message: Callback function to handle received messages
        """
        self.url = url
        self.symbols = symbols or []
        self.on_message = on_message
        self.ws = None
        self.thread = None
        self.connected = False

    def _on_open(self, ws):
        print("✅ Connected to Pocket Option WebSocket")
        self.connected = True
        # Subscribe to symbols
        for symbol in self.symbols:
            sub_msg = {
                "command": "subscribeMessage",
                "identifier": f"asset/{symbol}"
            }
            ws.send(json.dumps(sub_msg))
            print(f"📡 Subscribed to {symbol}")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if self.on_message:
                self.on_message(data)
        except Exception as e:
            print(f"⚠️ Error parsing message: {e}")

    def _on_error(self, ws, error):
        print(f"❌ WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print("🔌 WebSocket connection closed")
        self.connected = False
        # Auto-reconnect after 5 seconds
        time.sleep(5)
        self.connect()

    def connect(self):
        """Start WebSocket connection in a new thread"""
        def run():
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            self.ws.run_forever()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def send(self, message: dict):
        """Send raw message to WebSocket"""
        if self.connected and self.ws:
            self.ws.send(json.dumps(message))

    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
        self.connected = False


# Example usage
if __name__ == "__main__":
    def handle_message(data):
        print("📩 Received:", data)

    symbols = ["EURUSD_otc", "GBPUSD_otc"]  # Pocket Option OTC symbols

    ws_client = PocketOptionWS(symbols=symbols, on_message=handle_message)
    ws_client.connect()

    # Keep running
    while True:
        time.sleep(1)
