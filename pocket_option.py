# pocket_option.py
"""
Utility module for connecting to Pocket Option WebSocket.
Handles connection, subscriptions, and incoming price updates.
"""

import json
import websocket
import threading
import time


class PocketOptionWS:
    def __init__(self, on_message_callback=None):
        """
        Initialize WebSocket client for Pocket Option.

        :param on_message_callback: Function to handle incoming price data
        """
        self.ws = None
        self.thread = None
        self.on_message_callback = on_message_callback
        self.keep_running = False

        # Pocket Option WebSocket endpoint (replace if different for OTC/live data)
        self.url = "wss://ws.pocketoption.com/echo"

    def _on_open(self, ws):
        print("✅ Connected to Pocket Option WebSocket")

        # Example subscription (replace with actual Pocket Option subscription format)
        subscribe_msg = {
            "method": "subscribe",
            "params": {
                "symbol": "EURUSD_otc",  # Example symbol
                "interval": "M1"        # Example timeframe
            }
        }
        ws.send(json.dumps(subscribe_msg))
        print("📡 Subscribed to EURUSD_otc M1")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            # Debug: print incoming data
            # print("📩 Raw data:", data)

            # If there's a callback, forward price data
            if self.on_message_callback:
                self.on_message_callback(data)

        except Exception as e:
            print(f"⚠️ Error parsing message: {e}")

    def _on_error(self, ws, error):
        print(f"❌ WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print("🔌 WebSocket closed")

    def start(self):
        """Start WebSocket connection in a separate thread."""
        self.keep_running = True
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        def run():
            while self.keep_running:
                try:
                    self.ws.run_forever()
                except Exception as e:
                    print(f"⚠️ Connection error: {e}")
                    time.sleep(5)  # retry after delay

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop WebSocket connection."""
        self.keep_running = False
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join(timeout=2)
        print("🛑 Pocket Option WebSocket stopped")


# Quick test if run standalone
if __name__ == "__main__":
    def handle_data(msg):
        print("📊 Incoming data:", msg)

    po = PocketOptionWS(on_message_callback=handle_data)
    po.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        po.stop()
