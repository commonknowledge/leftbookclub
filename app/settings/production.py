from urllib.parse import urlparse

from .base import *

DEBUG = False
SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [os.getenv("BASE_URL", "")]

if os.getenv("AWS_S3_REGION_NAME"):
    DEFAULT_FILE_STORAGE = "app.storage.DigitalOceanSpacesStorage"
    AWS_S3_ADDRESSING_STYLE = "virtual"
    # like `fra1`
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
    # like `leftbookclub`
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    # like `https://fra1.digitaloceanspaces.com`
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    # can be ignored
    AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN")
    MEDIA_URL = os.getenv("MEDIA_URL")
else:
    MEDIA_ROOT = os.getenv(MEDIA_ROOT)
    MEDIA_URL = os.getenv("MEDIA_URL", "/media")


if os.getenv("MAILJET_API_KEY"):
    # if you don't already have this in settings
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@leftbookclub.com")
    # ditto (default from-email for Django errors)
    SERVER_EMAIL = DEFAULT_FROM_EMAIL
    ANYMAIL = {
        "SEND_DEFAULTS": {"envelope_sender": DEFAULT_FROM_EMAIL},
        "MAILJET_API_KEY": os.getenv("MAILJET_API_KEY"),
        "MAILJET_SECRET_KEY": os.getenv("MAILJET_SECRET_KEY"),
    }
    EMAIL_BACKEND = "anymail.backends.mailjet.EmailBackend"
elif os.getenv("MAILGUN_API_URL"):
    ANYMAIL = {
        "MAILGUN_API_URL": os.getenv("MAILGUN_API_URL"),
        "MAILGUN_API_KEY": os.getenv("MAILGUN_API_KEY"),
        "MAILGUN_SENDER_DOMAIN": os.getenv("MAILGUN_SENDER_DOMAIN"),
    }
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
    DEFAULT_FROM_EMAIL = f"noreply@{ANYMAIL['MAILGUN_SENDER_DOMAIN']}"
    ANYMAIL["SEND_DEFAULTS"] = ({"envelope_sender": DEFAULT_FROM_EMAIL},)
    # ditto (default from-email for Django errors)
    SERVER_EMAIL = f"admin@{ANYMAIL['MAILGUN_SENDER_DOMAIN']}"

WAGTAILTRANSFER_SECRET_KEY = os.getenv("WAGTAILTRANSFER_SECRET_KEY")
WAGTAILTRANSFER_SOURCES = {}

if os.getenv("WAGTAILTRANSFER_SECRET_KEY_STAGING"):
    WAGTAILTRANSFER_SOURCES["staging"] = {
        "BASE_URL": "https://lbc-staging.fly.dev/wagtail-transfer/",
        "SECRET_KEY": os.getenv("WAGTAILTRANSFER_SECRET_KEY_STAGING"),
    }

if os.getenv("WAGTAILTRANSFER_SECRET_KEY_PRODUCTION"):
    WAGTAILTRANSFER_SOURCES["production"] = {
        "BASE_URL": "https://lbc-production.fly.dev/wagtail-transfer/",
        "SECRET_KEY": os.getenv("WAGTAILTRANSFER_SECRET_KEY_PRODUCTION"),
    }


import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

SENTRY_DSN = os.getenv("SENTRY_DSN", None)
if SENTRY_DSN is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        environment=os.getenv("FLY_APP_NAME", None),
        release=os.getenv("GIT_SHA", None),
    )


try:
    from .local import *
except ImportError:
    pass
