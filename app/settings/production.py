from urllib.parse import urlparse

from .base import *

DEBUG = False
SECRET_KEY = os.getenv("SECRET_KEY")
BASE_URL = re.sub(r"/$", "", os.getenv("BASE_URL", ""))
ALLOWED_HOSTS = [urlparse(BASE_URL).netloc]

if os.getenv("AWS_S3_REGION_NAME"):
    DEFAULT_FILE_STORAGE = "app.storage.DigitalOceanSpacesStorage"
    AWS_S3_ADDRESSING_STYLE = "virtual"
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
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
        "MAILJET_API_KEY": os.getenv("MAILJET_API_KEY"),
        "MAILJET_SECRET_KEY": os.getenv("MAILJET_SECRET_KEY"),
        "SEND_DEFAULTS": {
            "envelope_sender": DEFAULT_FROM_EMAIL
        },
    }
    EMAIL_BACKEND = "anymail.backends.mailjet.EmailBackend"

WAGTAILTRANSFER_SECRET_KEY = os.getenv("WAGTAILTRANSFER_SECRET_KEY")

try:
    from .local import *
except ImportError:
    pass
