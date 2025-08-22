# credentials.py
import os

# Pocket Option credentials from environment variables
POCKET_SESSION_TOKEN = os.getenv("POCKET_SESSION_TOKEN")
POCKET_USER_ID = os.getenv("POCKET_USER_ID")
POCKET_ACCOUNT_URL = os.getenv("POCKET_ACCOUNT_URL")  # e.g., "cabinet/demo-quick-high-low" or real account path

# Optional: validate that the variables exist
if not POCKET_SESSION_TOKEN or not POCKET_USER_ID or not POCKET_ACCOUNT_URL:
    raise EnvironmentError(
        "Please set POCKET_SESSION_TOKEN, POCKET_USER_ID, and POCKET_ACCOUNT_URL in your environment variables (.env)"
    )
