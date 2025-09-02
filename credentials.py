# credentials.py

# Pocket Option credentials
sessionToken = "b651d1bb804319e18d46104a66f13197"
uid = "107618624"
currentUrl = "ACCOUNT_URL"

# Ensure credentials are set
if not sessionToken or not uid:
    raise EnvironmentError("Pocket Option credentials are not set in credentials.py")
