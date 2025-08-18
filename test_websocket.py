# test_websocket.py
import websocket

def on_message(ws, message):
    print("Received:", message)
    ws.close()  # close after one response

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("Sending message...")
    ws.send("Hello WebSocket from Termux!")

if __name__ == "__main__":
    websocket.enableTrace(True)  # shows connection logs
    ws = websocket.WebSocketApp(
        "wss://echo.websocket.events/",  # public echo server
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open
    ws.run_forever()
