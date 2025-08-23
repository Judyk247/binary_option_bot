"""
Handles login to Pocket Option using Selenium automation.
Also sets up a live WebSocket connection to stream price data.
"""

import os
import time
import threading
import websocket
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
PO_EMAIL = os.getenv("POCKET_OPTION_EMAIL")
PO_PASSWORD = os.getenv("POCKET_OPTION_PASSWORD")

# Correct login URL
PO_URL = "https://pocketoption.com/en/cabinet/login"
PO_WS_URL = "wss://chat-po.site/cabinet-client/socket.io/?EIO=4&transport=websocket"

# --- Selenium Automation ---
def start_browser(headless: bool = True):
    """Start a Chrome browser session."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    return driver

def login_pocket_option():
    """Logs into Pocket Option and returns an authenticated driver session."""
    if not PO_EMAIL or not PO_PASSWORD:
        raise ValueError("Pocket Option email/password not set in .env")

    driver = start_browser(headless=False)  # set True if running headless
    driver.get(PO_URL)
    time.sleep(3)

    # Enter email
    email_field = driver.find_element(By.NAME, "email")
    email_field.send_keys(PO_EMAIL)
    time.sleep(1)

    # Enter password and submit
    password_field = driver.find_element(By.NAME, "password")
    password_field.send_keys(PO_PASSWORD)
    password_field.send_keys(Keys.RETURN)
    time.sleep(5)

    if "dashboard" not in driver.current_url.lower():
        raise RuntimeError("Login failed. Check credentials.")

    print("✅ Successfully logged into Pocket Option")
    return driver

# --- WebSocket Integration ---
def send_heartbeat(ws):
    """Send ping every 5 seconds to keep connection alive"""
    while True:
        try:
            ws.send("2")  # Socket.IO ping
        except Exception as e:
            print("[HEARTBEAT ERROR]", e)
        time.sleep(5)

def on_open(ws):
    print("[OPEN] Connected to Pocket Option WebSocket")
    ws.send('42["getAssets", {}]')  # Request assets list
    threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

def on_message(ws, message):
    if message.startswith("42"):
        try:
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None
            print("[WS MESSAGE]", event, payload)
        except Exception as e:
            print("[WS ERROR parsing message]", e)

def on_close(ws, close_status_code, close_msg):
    print("[CLOSE] WebSocket closed:", close_status_code, close_msg)

def on_error(ws, error):
    print("[ERROR]", error)

def start_ws():
    """Start WebSocket connection with auto-reconnect"""
    while True:
        try:
            ws = websocket.WebSocketApp(
                PO_WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_close=on_close,
                on_error=on_error,
                header=["Origin: https://m.pocketoption.com"]
            )
            ws.run_forever()
        except Exception as e:
            print("[FATAL ERROR]", e)
        print("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)

# --- Main Execution ---
if __name__ == "__main__":
    driver = login_pocket_option()  # Selenium login
    print("Logged in. Title:", driver.title)

    # Start WebSocket in background thread
    threading.Thread(target=start_ws, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Exiting login automation + WebSocket")
        driver.quit()
