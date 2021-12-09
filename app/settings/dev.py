from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TEMPLATE_DEBUG = True
DJANGO_VITE_DEV_MODE = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-lt!8@q40mll#wdum^+n!y67i-_3k%1p-9k$5#s!ok2-o8wr7eh"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
BASE_URL = "http://localhost:8080"

DATABASES["default"]["CONN_MAX_AGE"] = 0

try:
    from .local import *
except ImportError:
    pass
