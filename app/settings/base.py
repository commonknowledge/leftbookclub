import os
import re
from datetime import timedelta

import dj_database_url

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

USE_WHITENOISE = os.getenv("USE_WHITENOISE", False) in (True, "True", "true", "t", 1)
# Application definition

INSTALLED_APPS = [
    "app",
    "mathfilters",
    "djmoney",
    "anymail",
    "wagtail_rangefilter",
    "rangefilter",
    "rest_framework",
    "groundwork.core",
    "groundwork.geo",
    "django_vite",
    "wagtailseo",
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
    "wagtail",
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
    "admin_list_controls",
    "mjml",
    "import_export",
    "oauth2_provider",
    "django.contrib.humanize",
    "django_dbq",
    "slippers",
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
    "django.middleware.security.SecurityMiddleware",
]

MIDDLEWARE += [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "livereload.middleware.LiveReloadScript",
    "app.middleware.update_stripe_customer_subscription",
    "app.middleware.frontend_backend_posthog_identity_linking",
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
                # "app.context_processors.user_data",
            ],
            "builtins": ["slippers.templatetags.slippers"],
        },
    }
]

WSGI_APPLICATION = "app.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases


PLATFORM_DATABASE_URL = os.getenv("DATABASE_URL", None)
ssl_require = os.getenv("REQUIRE_SSL", "True") == "True"  # Default to True

if os.getenv("SKIP_DB") != "1" and isinstance(PLATFORM_DATABASE_URL, str):
    DATABASES = {
        "default": dj_database_url.parse(
            re.sub(r"^postgres(ql)?", "postgis", PLATFORM_DATABASE_URL),
            conn_max_age=600,
            ssl_require=ssl_require,
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
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = False
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False

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
DJANGO_VITE_MANIFEST_PATH = DJANGO_VITE_ASSETS_PATH + "/.vite/manifest.json"

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
WAGTAILADMIN_BASE_URL = BASE_URL

WAGTAILIMAGES_IMAGE_MODEL = "app.CustomImage"

# Groundwork
SYNC_INTERVAL_DEFAULT_MINUTES = int(os.getenv("SYNC_INTERVAL_DEFAULT_MINUTES", 30))

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
SHOPIFY_BOOKS_COLLECTION_ID = os.environ.get(
    "SHOPIFY_BOOKS_COLLECTION_ID", "415349473513"
)
SHOPIFY_MERCH_COLLECTION_ID = os.environ.get(
    "SHOPIFY_MERCH_COLLECTION_ID", "415349407977"
)
SYNC_SHOPIFY_WEBHOOK_ENDPOINT = os.environ.get(
    "SYNC_SHOPIFY_WEBHOOK_ENDPOINT", "shopify/sync"
)
SHOPIFY_PRIVATE_APP_PASSWORD = os.environ.get("SHOPIFY_PRIVATE_APP_PASSWORD", None)
SHOPIFY_APP_API_SECRET = os.environ.get("SHOPIFY_APP_API_SECRET", "")
SHOPIFY_WEBHOOK_PATH = os.environ.get("SHOPIFY_WEBHOOK_PATH", "shopify/webhooks/")

# CSP
X_FRAME_OPTIONS = "SAMEORIGIN"

# menus
WAGTAILMENUS_FLAT_MENUS_HANDLE_CHOICES = (("footer", "Footer"),)

# MJML
MJML_BACKEND_MODE = "cmd"
MJML_EXEC_CMD = "node_modules/.bin/mjml"

# Posthog
POSTHOG_PUBLIC_TOKEN = os.getenv("POSTHOG_PUBLIC_TOKEN", None)
POSTHOG_URL = os.getenv("POSTHOG_URL", "https://app.posthog.com")
POSTHOG_DJANGO = {"distinct_id": lambda request: request.user and request.user.id}

# Google
GOOGLE_TAG_MANAGER = os.getenv("GOOGLE_TAG_MANAGER", None)
GOOGLE_TRACKING_ID = os.getenv("GOOGLE_TRACKING_ID", None)
GOOGLE_EVENT_ID = os.getenv("GOOGLE_EVENT_ID", None)

# Facebook
FACEBOOK_PIXEL = os.getenv("FACEBOOK_PIXEL", None)

# Mailchimp
MAILCHIMP_API_KEY = os.getenv("MAILCHIMP_API_KEY", None)
MAILCHIMP_SERVER_PREFIX = os.getenv("MAILCHIMP_SERVER_PREFIX", "us12")
MAILCHIMP_LIST_ID = os.getenv("MAILCHIMP_LIST_ID", "327021")

# Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN", None)
SENTRY_ORG_SLUG = os.getenv("SENTRY_ORG_SLUG", None)
SENTRY_PROJECT_ID = os.getenv("SENTRY_PROJECT_ID", None)

# Github
GIT_SHA = os.getenv("GIT_SHA", None)

# Render
RENDER_APP_NAME = os.getenv("RENDER_APP_NAME", None)

# Circle
CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY", None)
CIRCLE_COMMUNITY_ID = os.getenv("CIRCLE_COMMUNITY_ID", 42711)
CIRCLE_PER_PAGE = os.getenv("CIRCLE_PER_PAGE", 100)
SYNC_INTERVAL_MINUTES_CIRCLE_EVENTS = int(
    os.getenv("SYNC_INTERVAL_MINUTES_CIRCLE_EVENTS", SYNC_INTERVAL_DEFAULT_MINUTES)
)

# Mapbox
MAPBOX_PUBLIC_API_KEY = os.getenv("MAPBOX_PUBLIC_API_KEY", None)

### Error logging

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

STRIPE_TRACE_SAMPLE_RATE = float(
    os.getenv("STRIPE_TRACE_SAMPLE_RATE", 0.3 if STRIPE_LIVE_MODE else 1.0)
)

if SENTRY_DSN is not None:
    integrations = [DjangoIntegration()]

    if POSTHOG_PUBLIC_TOKEN is not None and SENTRY_PROJECT_ID is not None:
        from posthog.sentry.posthog_integration import (
            PostHogIntegration as PostHogSentryIntegration,
        )

        PostHogSentryIntegration.organization = SENTRY_ORG_SLUG
        integrations += [PostHogSentryIntegration()]

        MIDDLEWARE += [
            "posthog.sentry.django.PosthogDistinctIdMiddleware",
        ]

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=integrations,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=STRIPE_TRACE_SAMPLE_RATE,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        environment=RENDER_APP_NAME,
        release=GIT_SHA,
    )

USE_SILK = os.getenv("USE_SILK", False) in (True, "True", "true", "t", 1)

if USE_SILK:
    MIDDLEWARE += [
        "silk.middleware.SilkyMiddleware",
    ]

    INSTALLED_APPS += [
        "silk",
    ]

OAUTH2_PROVIDER = {
    "OIDC_ENABLED": True,
    "OIDC_RSA_PRIVATE_KEY": os.getenv("OIDC_RSA_PRIVATE_KEY", None),
    "SCOPES": {
        "openid": "OpenID Connect scope",
        # ... any other scopes that you use
    },
    "PKCE_REQUIRED": os.getenv("PKCE_REQUIRED", True) in (True, "True", "t", 1),
    "OAUTH2_VALIDATOR_CLASS": "app.oauth.CustomOAuth2Validator",
    "OIDC_ISS_ENDPOINT": os.getenv("OIDC_ISS_ENDPOINT", "")
    # ... any other settings you want
}

# OAUTH2_PROVIDER_APPLICATION_MODEL='app.CustomOAuth2Application'

JOBS = {
    "sync_shopify_products": {
        "tasks": ["app.management.commands.sync_shopify_products.run"],
    },
    "update_subscription": {
        "tasks": ["app.management.commands.update_subscription.run"],
    },
}


#### Cache

# Disable in development
WAGTAIL_CACHE = os.getenv("WAGTAIL_CACHE", False)

INSTALLED_APPS += ["wagtailcache"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.path.join(BASE_DIR, "cache"),
        "KEY_PREFIX": "wagtailcache",
        "TIMEOUT": int(
            os.getenv("WAGTAIL_CACHE_TIMEOUT_SECONDS", 60 * 60 * 24)
        ),  # in seconds
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

SLIPPERS_COMPONENT_TEMPLATE_SUBDIR = "components"
