import djstripe.settings
import shopify
import stripe
from django.apps import AppConfig
from django.conf import settings

from app.stripe_webhooks import *


class LeftBookClub(AppConfig):
    name = "app"
    verbose_name = "Left Book Club"

    def ready(self):
        stripe.api_key = djstripe.settings.djstripe_settings.STRIPE_SECRET_KEY
        stripe.api_version = "2020-08-27"
        shopify.Session(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        )
