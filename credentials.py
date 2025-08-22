import os

# Pocket Option credentials from environment variables
POCKET_SESSION_TOKEN = os.getenv("POCKET_SESSION_TOKEN")
POCKET_USER_ID = os.getenv("POCKET_USER_ID")

# Optional: validate that the variables exist
if not POCKET_SESSION_TOKEN or not POCKET_USER_ID:
    raise EnvironmentError(
        "Please set POCKET_SESSION_TOKEN and POCKET_USER_ID in your environment variables (.env)"
    )
