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
        # Implicitly connect a signal handlers decorated with @receiver.
        from . import signals

        self.configure_posthog()
        self.configure_shopify()

    def configure_shopify(self):
        stripe.api_key = djstripe.settings.djstripe_settings.STRIPE_SECRET_KEY
        stripe.api_version = "2020-08-27"
        shopify.Session(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        )
        print("--- 🛒 Shopify enabled ---")

    def configure_posthog(self):
        posthog.api_key = settings.POSTHOG_PUBLIC_TOKEN
        posthog.host = settings.POSTHOG_URL
        print("--- 🦔 Posthog enabled ---")


basic_posthog_event_properties = {
    "environment": settings.FLY_APP_NAME,
    "debug": settings.DEBUG,
    "base_url": settings.BASE_URL,
}
