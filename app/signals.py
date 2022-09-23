import shopify
import stripe
from django.dispatch import receiver
from djstripe import webhooks
from djstripe.models import Customer
from sentry_sdk import capture_exception
from shopify_webhook.signals import products_create, products_delete, products_update

from app import analytics
from app.models.wagtail import BookPage
from app.utils.mailchimp import tag_user_in_mailchimp
from app.utils.stripe import gift_recipient_subscription_from_code


@webhooks.handler("customer.subscription.deleted")
def cancel_gift_recipient_subscription(event, **kwargs):
    object = event.data.get("object", {})

    if (
        object.get("object", None) == "subscription"
        and object.get("metadata", {}).get("gift_mode", None) is not None
    ):
        promo_code = object.get("metadata", {}).get("promo_code", None)
        if promo_code is not None:
            recipient_subscription = gift_recipient_subscription_from_code(promo_code)
            stripe.Subscription.delete(recipient_subscription.id)
            # Analytics
            try:
                customer = Customer.objects.filter(id=object.get("customer")).first()
                if customer is not None and customer.subscriber is not None:
                    analytics.cancel_gift_card(customer.subscriber)
                    tag_user_in_mailchimp(
                        customer.subscriber,
                        tags_to_enable=["CANCELLED_GIFT_GIVER"],
                        tags_to_disable=["GIFT_GIVER"],
                    )
            except Exception as e:
                capture_exception(e)
                pass
    else:
        # Analytics
        try:
            customer = Customer.objects.filter(id=object.get("customer")).first()
            if (
                customer is not None
                and customer.subscriber is not None
                and customer.subscriber.active_subscription is None
            ):
                analytics.expire_membership(customer.subscriber)
                tag_user_in_mailchimp(
                    customer.subscriber,
                    tags_to_enable=["CANCELLED"],
                    tags_to_disable=["MEMBER"],
                )
        except Exception as e:
            capture_exception(e)
            pass


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
    BookPage.sync_from_shopify_product_id(product_id)


@receiver(products_delete)
def sync(*args, data: shopify.Product, **kwargs):
    from app.models.wagtail import BaseShopifyProductPage

    product_id = data.get("id")
    print("Product", product_id, "was deleted")
    BookPage.objects.filter(shopify_product_id=product_id).delete()
