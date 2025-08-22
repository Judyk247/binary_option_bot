import os

POCKET_SESSION_TOKEN = os.getenv("POCKET_SESSION_TOKEN")
POCKET_USER_ID = os.getenv("POCKET_USER_ID")
POCKET_ACCOUNT_MODE = os.getenv("POCKET_ACCOUNT_MODE", "demo")  # default to demo

if POCKET_ACCOUNT_MODE.lower() == "demo":
    POCKET_ACCOUNT_URL = "cabinet/demo-quick-high-low"
else:
    POCKET_ACCOUNT_URL = "cabinet/real-quick-high-low"

# Validate
if not POCKET_SESSION_TOKEN or not POCKET_USER_ID or not POCKET_ACCOUNT_URL:
    raise EnvironmentError(
        "Please set POCKET_SESSION_TOKEN, POCKET_USER_ID, and POCKET_ACCOUNT_MODE in your environment variables (.env)"
    )
