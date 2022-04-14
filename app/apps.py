import djstripe.settings
import shopify
import stripe
from django.apps import AppConfig
from django.conf import settings


class LeftBookClub(AppConfig):
    name = "app"
    verbose_name = "Left Book Club"

    def ready(self):
        stripe.api_key = djstripe.settings.djstripe_settings.STRIPE_SECRET_KEY
        shopify.Session(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        )
