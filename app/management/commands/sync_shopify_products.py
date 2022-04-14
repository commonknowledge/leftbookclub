import shopify
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import BookPage


class Command(BaseCommand):
    help = "Create BookPage for each Shopify product"

    @transaction.atomic
    def handle(self, *args, **options):
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            cache.clear()
            book_ids = shopify.CollectionListing.find(
                settings.SHOPIFY_COLLECTION_ID
            ).product_ids()
            for book in book_ids:
                BookPage.get_for_product(book)

            # TODO: also list merch
            # products = shopify.Product.find(collection=settings.SHOPIFY_COLLECTION_ID)
            # for product in products:
            #     ShopifyProductPage.get_for_product(id=product.id)
