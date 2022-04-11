import djstripe.settings
import stripe
from django.apps import AppConfig


class LeftBookClub(AppConfig):
    name = "app"
    verbose_name = "Left Book Club"

    def ready(self):
        stripe.api_key = djstripe.settings.djstripe_settings.STRIPE_SECRET_KEY
