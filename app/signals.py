import shopify
import stripe
from django.dispatch import receiver
from djstripe import webhooks
from shopify_webhook.signals import products_create, products_update

from app.models.wagtail import BookPage
from app.utils.stripe import gift_recipient_subscription_from_code


@webhooks.handler("customer.subscription.deleted")
def cancel_gift_recipient_subscription(event, **kwargs):
    # update their situation on mailchimp
    object = event.data.get("object", {})
    if (
        object.get("object", None) == "subscription"
        and object.get("metadata", {}).get("gift_mode", None) is not None
    ):
        promo_code = object.get("metadata", {}).get("promo_code", None)
        recipient_subscription = gift_recipient_subscription_from_code(promo_code)
        stripe.Subscription.delete(recipient_subscription.id)
        # TODO: send them an email
        # update their situation on mailchimp


@receiver(products_update)
def sync(*args, data: shopify.Product, **kwargs):
    from app.models.wagtail import BaseShopifyProductPage

    product_id = data.get("id")
    print("Product", product_id, "was updated")
    BookPage.sync_from_shopify_product_id(product_id)


@receiver(products_create)
def sync(*args, data: shopify.Product, **kwargs):
    from app.models.wagtail import BaseShopifyProductPage

    product_id = data.get("id")
    print("Product", product_id, "was created")
    BookPage.sync_shopify_products_to_pages()
