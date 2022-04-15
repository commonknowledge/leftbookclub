import shopify
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import BaseShopifyProductPage


class Command(BaseCommand):
    help = "Create BookPage for each Shopify product"

    @transaction.atomic
    def handle(self, *args, **options):
        BaseShopifyProductPage.sync_shopify_products_to_pages()
