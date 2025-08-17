# pocket_option_integration.py
"""
Pocket Option integration module.
Handles login + real-time price streaming (no auto-trading).
⚠️ NOTE: Pocket Option does not provide an official API. 
This uses their internal WebSocket protocol (unofficial).
"""

import os
import json
import logging
import websocket
import threading
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
PO_EMAIL = os.getenv("PO_EMAIL")
PO_PASSWORD = os.getenv("PO_PASSWORD")

class PocketOptionClient:
    def __init__(self, email: str, password: str, on_quote=None):
        """
        Args:
            email (str): Pocket Option account email
            password (str): Pocket Option account password
            on_quote (callable): Function to call on new price update
                                 signature: fn(symbol: str, price: float)
        """
        self.email = email
        self.password = password
        self.ws = None
        self.connected = False
        self.quotes = {}
        self._lock = threading.Lock()
        self.on_quote = on_quote

    def connect(self):
        """Connect to Pocket Option WebSocket server."""
        ws_url = "wss://ws.pocketoption.com:8080/"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_open=self._on_open,
            on_close=self._on_close,
            on_error=self._on_error
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def _on_open(self, ws):
        logging.info("✅ Connected to Pocket Option WebSocket.")
        self.connected = True
        # Send login payload
        auth_payload = {
            "cmd": "auth",
            "email": self.email,
            "password": self.password
        }
        ws.send(json.dumps(auth_payload))

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if "quote" in data:
                symbol = data["quote"]["symbol"]
                price = float(data["quote"]["price"])
                with self._lock:
                    self.quotes[symbol] = price
                # Forward to callback (dashboard/strategy)
                if self.on_quote:
                    self.on_quote(symbol, price)
        except Exception as e:
            logging.error(f"Message parse error: {e}")

    def _on_close(self, ws, close_status_code, close_msg):
        logging.warning("⚠️ Pocket Option WebSocket closed.")
        self.connected = False

    def _on_error(self, ws, error):
        logging.error(f"❌ Pocket Option WebSocket error: {error}")
        self.connected = False

    def get_price(self, symbol: str) -> float:
        """Get latest cached price for a symbol."""
        with self._lock:
            return self.quotes.get(symbol)


# Example usage
if __name__ == "__main__":
    def print_quote(symbol, price):
        print(f"📈 {symbol} = {price}")

    client = PocketOptionClient(PO_EMAIL, PO_PASSWORD, on_quote=print_quote)
    client.connect()
