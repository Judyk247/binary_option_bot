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
import time
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
        self.keep_running = False

        # WebSocket URL for live/demo Pocket Option
        self.ws_url = "wss://events-po.com/socket.io/?EIO=4&transport=websocket"

    def _heartbeat(self):
        """Send ping every 5 seconds to keep connection alive"""
        while self.keep_running and self.ws:
            try:
                self.ws.send("2")  # Socket.IO ping
            except Exception as e:
                logging.warning(f"Heartbeat error: {e}")
            time.sleep(5)

    def _on_open(self, ws):
        logging.info("✅ Connected to Pocket Option WebSocket.")
        self.connected = True
        # Send login/auth payload
        auth_payload = {
            "cmd": "auth",
            "email": self.email,
            "password": self.password
        }
        ws.send(json.dumps(auth_payload))
        # Start heartbeat thread
        threading.Thread(target=self._heartbeat, daemon=True).start()

    def _on_message(self, ws, message):
        if message.startswith("42"):
            try:
                data = json.loads(message[2:])
                event = data[0]
                payload = data[1] if len(data) > 1 else None

                # Example: handle quotes data
                if event == "quote" and payload:
                    symbol = payload["symbol"]
                    price = float(payload["price"])
                    with self._lock:
                        self.quotes[symbol] = price
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

    def connect(self):
        """Start WebSocket connection with auto-reconnect."""
        self.keep_running = True

        def run():
            while self.keep_running:
                try:
                    self.ws = websocket.WebSocketApp(
                        self.ws_url,
                        on_open=self._on_open,
                        on_message=self._on_message,
                        on_close=self._on_close,
                        on_error=self._on_error,
                        header=["Origin: https://m.pocketoption.com"]  # Essential for live connection
                    )
                    self.ws.run_forever()
                except Exception as e:
                    logging.warning(f"Connection error: {e}")
                logging.info("⏳ Reconnecting in 5 seconds...")
                time.sleep(5)

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        """Stop WebSocket connection."""
        self.keep_running = False
        if self.ws:
            self.ws.close()
        logging.info("🛑 Pocket Option WebSocket stopped.")

    def get_price(self, symbol: str) -> float:
        """Get latest cached price for a symbol."""
        with self._lock:
            return self.quotes.get(symbol)


# Quick test if run standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def print_quote(symbol, price):
        print(f"📈 {symbol} = {price}")

    client = PocketOptionClient(PO_EMAIL, PO_PASSWORD, on_quote=print_quote)
    client.connect()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.stop()
