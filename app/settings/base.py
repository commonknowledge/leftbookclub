import os
import re

import dj_database_url

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/


# Application definition

INSTALLED_APPS = [
    "app",
    "mathfilters",
    "djmoney",
    "anymail",
    "rest_framework",
    "groundwork.core",
    "groundwork.geo",
    "django_vite",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.core",
    "wagtail.contrib.settings",
    "wagtail_transfer",
    "taggit",
    "modelcluster",
    "livereload",
    "djstripe",
    "django_bootstrap5",
    "wagtailautocomplete",
    "django_countries",
    "django_gravatar",
    "active_link",
    "wagtailfontawesome",
    # "wagtail_transfer",
    "django.contrib.gis",
    "django.contrib.admin",
    "django.contrib.auth",
    # 'allauth.socialaccount.providers.auth0',
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "wagtail.contrib.routable_page",
    "wagtail.contrib.modeladmin",
    "wagtailmenus",
    "wagtailseo",
    "admin_list_controls",
    "mjml",
    "import_export",
]

IMPORT_EXPORT_USE_TRANSACTIONS = True

# if (
#     os.environ.get("MJML_APPLICATION_ID", None) is not None
#     and os.environ.get("MJML_SECRET_KEY", None) is not None
# ):
#     INSTALLED_APPS += ["mjml"]
# else:
#     print("Warning: MJML is not installed")

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "livereload.middleware.LiveReloadScript",
    "app.middleware.update_stripe_customer_subscription",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
                "wagtailmenus.context_processors.wagtailmenus",
                "app.context_processors.settings",
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

PLATFORM_DATABASE_URL = os.getenv("DATABASE_URL", None)

if os.getenv("SKIP_DB") != "1" and isinstance(PLATFORM_DATABASE_URL, str):
    DATABASES = {
        "default": dj_database_url.parse(
            re.sub(r"^postgres(ql)?", "postgis", PLATFORM_DATABASE_URL),
            conn_max_age=600,
            ssl_require=False,
        )
    }

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "app.User"

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_DISPLAY = "app.models.django.custom_user_casual_name"

ACCOUNT_FORMS = {
    # 'login': 'allauth.account.forms.LoginForm',
    "signup": "app.forms.MemberSignupForm",
    # 'add_email': 'allauth.account.forms.AddEmailForm',
    # 'change_password': 'allauth.account.forms.ChangePasswordForm',
    # 'set_password': 'allauth.account.forms.SetPasswordForm',
    # 'reset_password': 'allauth.account.forms.ResetPasswordForm',
    # 'reset_password_from_key': 'allauth.account.forms.ResetPasswordKeyForm',
    # 'disconnect': 'allauth.socialaccount.forms.DisconnectForm',
}

LOGIN_REDIRECT_URL = "/"

## Laravel-compliant password hashing

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.BCryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-gb"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]


DJANGO_VITE_ASSETS_PATH = BASE_DIR + "/vite"
DJANGO_VITE_MANIFEST_PATH = DJANGO_VITE_ASSETS_PATH + "/manifest.json"

STATICFILES_DIRS = [
    DJANGO_VITE_ASSETS_PATH,
]


# ManifestStaticFilesStorage is recommended in production, to prevent outdated
# JavaScript / CSS assets being served from cache (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/3.2/ref/contrib/staticfiles/#manifeststaticfilesstorage
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# The absolute path to the directory where collectstatic will collect static files for deployment.
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"


DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ]
}


# Logging

DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
        },
    },
}

INTERNAL_IPS = [
    "127.0.0.1",
]

# Wagtail

WAGTAIL_SITE_NAME = "Left Book Club"
BASE_URL = re.sub(r"/$", "", os.getenv("BASE_URL", "http://localhost:8000"))

WAGTAILIMAGES_IMAGE_MODEL = "app.CustomImage"

# dj-stripe

STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "sk_live_")
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "sk_test_")
STRIPE_LIVE_PUBLIC_KEY = os.environ.get("STRIPE_LIVE_PUBLIC_KEY", "pk_live_")
STRIPE_TEST_PUBLIC_KEY = os.environ.get("STRIPE_TEST_PUBLIC_KEY", "pk_test_")
STRIPE_LIVE_MODE = os.environ.get("STRIPE_LIVE_MODE", "False").lower() in (
    "true",
    "1",
    "t",
)
DJSTRIPE_WEBHOOK_VALIDATION = "verify_signature"
DJSTRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", None)
DJSTRIPE_USE_NATIVE_JSONFIELD = (
    True  # We recommend setting to True for new installations
)
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# Shopify
SHOPIFY_DOMAIN = os.environ.get("SHOPIFY_DOMAIN", "left-book-club-shop.myshopify.com")
SHOPIFY_STOREFRONT_ACCESS_TOKEN = os.environ.get(
    "SHOPIFY_STOREFRONT_ACCESS_TOKEN", "a65d1227c3865ae25999a6d24d2106e0"
)
SHOPIFY_COLLECTION_ID = os.environ.get("SHOPIFY_COLLECTION_ID", "402936398057")
SHOPIFY_PRIVATE_APP_PASSWORD = os.environ.get("SHOPIFY_PRIVATE_APP_PASSWORD", None)
SHOPIFY_APP_API_SECRET = os.environ.get("SHOPIFY_APP_API_SECRET", "")

# CSP
X_FRAME_OPTIONS = "SAMEORIGIN"

# menus

WAGTAILMENUS_FLAT_MENUS_HANDLE_CHOICES = (("footer", "Footer"),)

# MJML
MJML_BACKEND_MODE = "cmd"
MJML_EXEC_CMD = "node_modules/.bin/mjml"

# Posthog
POSTHOG_PUBLIC_TOKEN = os.getenv("POSTHOG_PUBLIC_TOKEN", None)
POSTHOG_URL = "https://app.posthog.com"

# Google
GOOGLE_TRACKIND_ID = os.getenv("GOOGLE_TRACKING_ID", None)