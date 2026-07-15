import os

os.environ["SENTRY_ENABLED"] = "false"
os.environ.setdefault("PROFILE_SERVICE_URL", "http://profiles.invalid")
os.environ.setdefault("VACANCY_SERVICE_URL", "http://vacancy.invalid")
os.environ.setdefault("VACANCY_SERVICE_TIMEOUT_SECONDS", "5")
os.environ.setdefault("MAIN_BE_SERVICE_KEY", "test-service-key")
