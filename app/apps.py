import stripe
from django.apps import AppConfig
from django.conf import settings


class LeftBookClub(AppConfig):
    name = "app"
    verbose_name = "Left Book Club"

    def ready(self):
        stripe.api_key = settings.STRIPE_API_KEY
