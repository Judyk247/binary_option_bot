import os

POCKET_SESSION_TOKEN = os.getenv("POCKET_SESSION_TOKEN")
POCKET_USER_ID = os.getenv("POCKET_USER_ID")

# Always use live/real mode
POCKET_ACCOUNT_MODE = "real"
POCKET_ACCOUNT_URL = "cabinet/real-quick-high-low"

# Validate
if not POCKET_SESSION_TOKEN or not POCKET_USER_ID:
    raise EnvironmentError(
        "Please set POCKET_SESSION_TOKEN and POCKET_USER_ID in your environment variables (.env)"
    )
