"""
Utility module for connecting to Pocket Option WebSocket.
Handles connection, subscriptions, incoming price updates, heartbeat, and auto-reconnect.
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

        # Pocket Option WebSocket endpoint (live/OTC)
        self.url = "wss://events-po.com/socket.io/?EIO=4&transport=websocket"

    def _on_open(self, ws):
        print("✅ Connected to Pocket Option WebSocket")
        # Example: request assets list or subscribe to default symbols if needed
        ws.send('42["getAssets", {}]')
        print("📡 Requested assets list")

        # Start heartbeat in background
        threading.Thread(target=self._heartbeat, args=(ws,), daemon=True).start()

    def _on_message(self, ws, message):
        if message.startswith("42"):
            try:
                data = json.loads(message[2:])
                event = data[0]
                payload = data[1] if len(data) > 1 else None

                # Forward to callback
                if self.on_message_callback:
                    self.on_message_callback(event, payload)

            except Exception as e:
                print(f"⚠️ Error parsing message: {e}")

    def _on_error(self, ws, error):
        print(f"❌ WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print("🔌 WebSocket closed:", close_status_code, close_msg)

    def _heartbeat(self, ws):
        """Send ping every 5 seconds to keep the connection alive"""
        while self.keep_running:
            try:
                ws.send("2")  # Socket.IO ping
            except Exception as e:
                print(f"⚠️ Heartbeat error: {e}")
            time.sleep(5)

    def start(self):
        """Start WebSocket connection in a separate thread with auto-reconnect."""
        self.keep_running = True

        def run():
            while self.keep_running:
                try:
                    self.ws = websocket.WebSocketApp(
                        self.url,
                        on_open=self._on_open,
                        on_message=self._on_message,
                        on_error=self._on_error,
                        on_close=self._on_close,
                        header=["Origin: https://m.pocketoption.com"]  # Important for live connection
                    )
                    self.ws.run_forever()
                except Exception as e:
                    print(f"⚠️ Connection error: {e}")
                print("⏳ Reconnecting in 5 seconds...")
                time.sleep(5)

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
    def handle_data(event, payload):
        print("📊 Incoming event:", event, "Payload:", payload)

    po = PocketOptionWS(on_message_callback=handle_data)
    po.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        po.stop()
