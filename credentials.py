# credentials.py


sessionToken = "b651d1bb804319e18d46104a66f13197"
uid = "107618624"
ACCOUNT_URL = "cabinet"

# If any of the above are missing, raise an error               if not sessionToken or not uid or not ACCOUNT_URL:
    raise EnvironmentError("Pocket Option credentials are not set in credentials.py")
