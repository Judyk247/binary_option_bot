# login_automation.py
"""
Handles login to Pocket Option using Selenium automation.
Relies on environment variables for security.
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

PO_EMAIL = os.getenv("POCKET_OPTION_EMAIL")
PO_PASSWORD = os.getenv("POCKET_OPTION_PASSWORD")
PO_URL = "https://pocketoption.com/en/cabinet/"


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

    driver = start_browser(headless=False)  # set True if you want headless on Render
    driver.get(PO_URL)

    # Wait for login form
    time.sleep(3)

    # Find email field and enter
    email_field = driver.find_element(By.NAME, "email")
    email_field.send_keys(PO_EMAIL)
    time.sleep(1)

    # Find password field and enter
    password_field = driver.find_element(By.NAME, "password")
    password_field.send_keys(PO_PASSWORD)
    password_field.send_keys(Keys.RETURN)

    # Wait for login success (dashboard load)
    time.sleep(5)

    if "dashboard" not in driver.current_url.lower():
        raise RuntimeError("Login failed. Please check credentials.")

    print("✅ Successfully logged into Pocket Option")

    return driver


if __name__ == "__main__":
    session = login_pocket_option()
    # Example: print the page title after login
    print("Logged in. Title:", session.title)
