import os

os.environ["SENTRY_ENABLED"] = "false"
os.environ.setdefault("PROFILE_SERVICE_URL", "http://profiles.invalid")
os.environ.setdefault("MAIN_BE_SERVICE_KEY", "test-service-key")
