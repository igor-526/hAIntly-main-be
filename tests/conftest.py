import os

os.environ["SENTRY_ENABLED"] = "false"
os.environ.setdefault("PROFILE_SERVICE_URL", "http://profiles.invalid")
