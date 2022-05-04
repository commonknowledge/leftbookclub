import djstripe.settings
import posthog
import shopify
import stripe
from django.apps import AppConfig
from django.conf import settings


class LeftBookClub(AppConfig):
    name = "app"
    verbose_name = "Left Book Club"

    def ready(self):
        stripe.api_key = djstripe.settings.djstripe_settings.STRIPE_SECRET_KEY
        stripe.api_version = "2020-08-27"
        shopify.Session(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        )
        # Implicitly connect a signal handlers decorated with @receiver.
        from . import signals

        if settings.POSTHOG_PUBLIC_TOKEN:
            posthog.api_key = settings.POSTHOG_PUBLIC_TOKEN
            posthog.host = settings.POSTHOG_URL
        if settings.DEBUG:
            posthog.disabled = True
