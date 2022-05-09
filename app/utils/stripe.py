from typing import TYPE_CHECKING, Tuple, Union

from datetime import datetime

import djstripe.models
import stripe
from dateutil.relativedelta import relativedelta

if TYPE_CHECKING:
    # see https://stackoverflow.com/a/39757388/1053937
    from app.models.django import User

from app.utils import include_keys


def is_real_gift_code(code):
    possible_codes = stripe.PromotionCode.list(code=code)
    return (
        len(possible_codes) > 0
        and possible_codes[0].max_redemptions is not None
        and possible_codes[0].metadata.get("gift_giver_subscription", False)
    )


def is_redeemable_gift_code(code):
    possible_codes = stripe.PromotionCode.list(code=code).data
    return (
        len(possible_codes) > 0
        and possible_codes[0].max_redemptions is not None
        and possible_codes[0].max_redemptions > possible_codes[0].times_redeemed
        and possible_codes[0].metadata.get("gift_giver_subscription", False)
    )


def gift_giver_subscription_from_code(
    code: str,
) -> Union[djstripe.models.Subscription, None]:
    promo_code = None

    possible_codes = stripe.PromotionCode.list(code=code).data
    if len(possible_codes) > 0:
        promo_code = possible_codes[0]
    else:
        # In case you actually passed the promo code ID
        promo_code = stripe.PromotionCode.retrieve(code)

    if promo_code:
        subscription_id = promo_code.metadata.get("gift_giver_subscription", None)

        if subscription_id:
            return djstripe.models.Subscription.sync_from_stripe_data(
                stripe.Subscription.retrieve(subscription_id)
            )
    return None


def gift_recipient_subscription_from_code(
    code_or_id: str,
) -> Union[djstripe.models.Subscription, None]:
    promo_code_id = None

    if code_or_id.startswith("promo_"):
        promo_code_id = code_or_id
    else:
        possible_codes = stripe.PromotionCode.list(code=code_or_id).data
        if len(possible_codes) > 0:
            promo_code_id = possible_codes[0].id

    if promo_code_id:
        return djstripe.models.Subscription.objects.filter(
            metadata__promo_code=promo_code_id
        ).first()


def subscription_with_promocode(
    sub: Union[stripe.Subscription, djstripe.models.Subscription]
):
    promo_code_id = sub.metadata.get("promo_code", None)
    if promo_code_id is not None:
        promocode = stripe.PromotionCode.retrieve(promo_code_id)
        setattr(sub, "promo_code", promocode)
    return sub


def get_shipping_product() -> djstripe.models.Product:
    shipping_product = None
    product_name = "Shipping"
    metadata_key = "shipping"
    metadata_value = "True"
    shipping_products = stripe.Product.search(
        query=f'active:"true" AND name:"{product_name}" AND metadata["{metadata_key}"]:"{metadata_value}"',
    ).data
    if len(shipping_products) > 0:
        shipping_product = shipping_products[0]
    else:
        shipping_product = stripe.Product.create(
            name=product_name,
            unit_label="delivery",
            metadata={metadata_key: metadata_value},
        )
    dj_shipping_product = djstripe.models.Product.sync_from_stripe_data(
        shipping_product
    )
    return dj_shipping_product


def get_gift_card_coupon(product: djstripe.models.Product) -> djstripe.models.Coupon:
    coupon_name = f"Gift Card: {product.name}"[:40]

    coupon = djstripe.models.Coupon.objects.filter(
        metadata__gift_product_id=product.id
    ).first()

    if coupon is None:
        shipping_product = get_shipping_product()
        if shipping_product is None:
            raise ValueError("Couldn't get shipping product")

        coupon = stripe.Coupon.create(
            name=coupon_name,
            percent_off=100,
            duration="forever",
            applies_to={"products": [product.id, shipping_product.id]},
            metadata={
                # Required because dj-stripe does not yet save the applied_to field
                # and stripe does not supporting querying coupons by applied_to
                # but we nonetheless need a way to query for it.
                # We can do this with metadata.
                "gift_product_id": product.id
            },
        )
        coupon = djstripe.models.Coupon.sync_from_stripe_data(coupon)

    return coupon


def recreate_one_off_stripe_price(price: stripe.Price):
    return {
        "unit_amount_decimal": price.unit_amount,
        "currency": price.currency,
        "product": price.product.id,
        "recurring": include_keys(
            price.recurring,
            (
                "interval",
                "interval_count",
            ),
        ),
    }


def create_one_off_shipping_price_data_for_price(price: stripe.Price, zone):
    shipping_product = get_shipping_product()
    return {
        "currency": zone.rate_currency,
        "unit_amount_decimal": zone.rate.amount * 100,
        "product": shipping_product.id,
        "recurring": include_keys(
            price.recurring,
            (
                "interval",
                "interval_count",
            ),
        ),
        "metadata": create_shipping_zone_metadata(zone),
    }


def create_shipping_zone_metadata(zone):
    return {"shipping": True, "shipping_zone": zone.code}


def configure_gift_giver_subscription_and_code(
    gift_giver_subscription_id: str, gift_giver_user_id, metadata={}, code: str = None
) -> Tuple[stripe.PromotionCode, djstripe.models.Subscription]:
    gift_giver_subscription = stripe.Subscription.modify(
        gift_giver_subscription_id, metadata={"gift_mode": True}
    )
    dj_sub = djstripe.models.Subscription.sync_from_stripe_data(gift_giver_subscription)

    # Get giftable product data
    product = get_primary_product_for_djstripe_subscription(dj_sub)
    if product is None:
        raise ValueError("This subscription doesn't have a giftable product.")

    # Get or create coupon, based on the membership product
    coupon = get_gift_card_coupon(product)

    # Optionally explicitly set the customer-facing code
    promo_code_extras = {}
    if code is not None:
        promo_code_extras["code"] = code

    promo_code = stripe.PromotionCode.create(
        coupon=coupon.id,
        max_redemptions=1,
        metadata={
            "gift_giver_subscription": gift_giver_subscription_id,
            "related_django_user": gift_giver_user_id,
            **metadata,
        },
        **promo_code_extras,
    )

    gift_giver_subscription = stripe.Subscription.modify(
        gift_giver_subscription_id,
        metadata={"promo_code": promo_code.id, **metadata},
    )

    gift_giver_subscription = djstripe.models.Subscription.sync_from_stripe_data(
        gift_giver_subscription
    )

    return promo_code, gift_giver_subscription


def create_gift_recipient_subscription(
    gift_giver_subscription: djstripe.models.Subscription, user: "User", metadata={}
) -> djstripe.models.Subscription:
    from app.models.stripe import ShippingZone

    if user.stripe_customer is None:
        djstripe.models.Customer.create(user)

    # Update stripe data so we're working with the latest statuses
    fresh_sub = stripe.Subscription.retrieve(gift_giver_subscription.id)
    gift_giver_subscription = djstripe.models.Subscription.sync_from_stripe_data(
        fresh_sub
    )

    # Get number of months from gift_giver_subscription.metadata.get('promo_code_id') -> pc.coupon.duration_in_months
    promo_code_id = gift_giver_subscription.metadata.get("promo_code")
    # promo_code = stripe.PromotionCode.retrieve(promo_code_id)

    items = []
    for si in gift_giver_subscription.items.all():
        if si.price.metadata.get("shipping_zone", None) is not None:
            zone = ShippingZone.get_for_code(
                code=si.price.metadata.get("shipping_zone", "ROW")
            )
            items.append(
                {
                    # Shipping
                    "price_data": create_one_off_shipping_price_data_for_price(
                        si.price, zone
                    ),
                    "quantity": si.quantity,
                    "metadata": {"primary": True},
                }
            )
        else:
            # Could we reuse MembershipPrice?
            # Yes, if we knew the (wagtail) price.id and product.id
            # Product ID comes from the si.price
            # Wagtail Price ID... we could potentially put on the metadata?
            items.append(
                {
                    # Membership
                    "price_data": recreate_one_off_stripe_price(si.price),
                    "quantity": si.quantity,
                    "metadata": {"shipping": True},
                }
            )

    args = dict(
        customer=user.stripe_customer.id,
        items=items,
        promotion_code=promo_code_id,
        payment_behavior="allow_incomplete",
        off_session=True,
        metadata={
            "gift_giver_subscription": gift_giver_subscription.id,
            "promo_code": promo_code_id,
            **metadata,
        },
    )
    subscription = stripe.Subscription.create(**args)

    # For easy forward access
    stripe.Subscription.modify(
        gift_giver_subscription.id,
        metadata={"gift_recipient_subscription": subscription.id},
    )

    subscription = djstripe.models.Subscription.sync_from_stripe_data(subscription)
    user.refresh_stripe_data()

    return subscription


def get_primary_product_for_djstripe_subscription(
    sub: djstripe.models.Subscription,
) -> djstripe.models.Product:
    if sub.plan is not None and sub.plan.product is not None:
        return sub.plan.product
    sis = []
    if sub.plan is not None and sub.plan.subscription_items.count() > 0:
        sis = sub.plan.subscription_items.all()
    elif sub.items.count() > 0:
        sis = sub.items.all()
    if sis is not None and len(sis) > 0:
        for si in sis:
            if "shipping" not in si.plan.product.name.lower():
                return si.plan.product


def get_shipping_product_for_djstripe_subscription(sub):
    sis = []
    if sub.plan is not None and sub.plan.subscription_items.count() > 0:
        sis = sub.plan.subscription_items.all()
    elif sub.items.count() > 0:
        sis = sub.items.all()
    if sis is not None and len(sis) > 0:
        for si in sis:
            if si.plan.product is not None and (
                "shipping" in si.plan.product.name.lower()
                or si.plan.product.metadata.get("shipping", None) is not None
            ):
                return si.plan.product
