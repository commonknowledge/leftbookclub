from urllib.parse import urlparse

from .base import *

DEBUG = False
SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", BASE_URL).split(",")


MIDDLEWARE += [
    "redirect_to_non_www.middleware.RedirectToNonWww",
]

#### File storage

# like `fra1`
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", None)
# like `leftbookclub`
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", None)
# like `https://fra1.digitaloceanspaces.com`
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", None)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
# can be ignored
AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN", None)
#
USE_S3_FOR_STATIC_FILES = os.getenv("USE_S3_FOR_STATIC_FILES", "1") == "1"

if AWS_S3_REGION_NAME is not None:
    AWS_S3_ADDRESSING_STYLE = "virtual"
    DEFAULT_FILE_STORAGE = "app.storage.DigitalOceanSpacesStorage"
    ### Media
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = (
        (
            f"https://{AWS_S3_CUSTOM_DOMAIN}"
            if AWS_S3_CUSTOM_DOMAIN
            else AWS_S3_ENDPOINT_URL
        )
        + "/"
        + PUBLIC_MEDIA_LOCATION.lstrip("/").rstrip("/")
        + "/"
    )
    DEFAULT_FILE_STORAGE = "app.storage.MediaStorage"
    ### Static
    if USE_S3_FOR_STATIC_FILES:
        STATIC_LOCATION = "static"
        STATIC_URL = (
            (
                f"https://{AWS_S3_CUSTOM_DOMAIN}"
                if AWS_S3_CUSTOM_DOMAIN
                else AWS_S3_ENDPOINT_URL.rstrip("/")
            )
            + "/"
            + STATIC_LOCATION.lstrip("/").rstrip("/")
            + "/"
        )
        STATICFILES_STORAGE = "app.storage.StaticStorage"
else:
    MEDIA_ROOT = os.getenv(MEDIA_ROOT)
    MEDIA_URL = os.getenv("MEDIA_URL", "/media/")


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
    ANYMAIL["SEND_DEFAULTS"] = {"envelope_sender": DEFAULT_FROM_EMAIL}
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


try:
    from .local import *
except ImportError:
    pass
