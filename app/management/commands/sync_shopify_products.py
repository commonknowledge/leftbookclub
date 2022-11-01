import shopify
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import BookPage
from app.models.wagtail import MerchandisePage


class Command(BaseCommand):
    help = "Sync shopify products"

    @transaction.atomic
    def handle(self, *args, **options):
        BookPage.sync_shopify_products_to_pages()
        MerchandisePage.sync_shopify_products_to_pages()
