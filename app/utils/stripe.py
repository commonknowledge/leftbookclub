from typing import Union

from datetime import datetime

import djstripe.models
import stripe
from dateutil.relativedelta import relativedelta

from app.utils import include_keys


def is_real_gift_code(code):
    possible_codes = stripe.PromotionCode.list(code=code)
    if len(possible_codes) > 0:
        return True
    return False


def is_redeemable_gift_code(code):
    possible_codes = stripe.PromotionCode.list(code=code).data
    if (
        len(possible_codes) > 0
        and possible_codes[0].max_redemptions > possible_codes[0].times_redeemed
    ):
        return True
    return False


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
    promo_code = None

    if code_or_id.startswith("promo_"):
        possible_codes = stripe.PromotionCode.list(code=code_or_id).data
        if len(possible_codes) > 0:
            promo_code = possible_codes[0]

    if promo_code:
        return djstripe.models.Subscription.objects.filter(
            metadata__promo_code=promo_code.id
        ).first()


def subscription_with_promocode(
    sub: Union[stripe.Subscription, djstripe.models.Subscription]
):
    promo_code_id = sub.metadata.get("promo_code", None)
    if promo_code_id is not None:
        promocode = stripe.PromotionCode.retrieve(promo_code_id)
        setattr(sub, "promo_code", promocode)
    return sub


def get_shipping_product():
    shipping_product = djstripe.models.Product.objects.filter(
        metadata__shipping__isnull=False, active=True
    ).first()
    if shipping_product is None:
        stripe_shipping_product = stripe.Product.create(
            name="Shipping", unit_label="delivery", metadata={"shipping": True}
        )
        shipping_product = djstripe.models.Product.sync_from_stripe_data(
            stripe_shipping_product
        )
    return shipping_product


def recreate_one_off_stripe_price(price: stripe.Price):
    return {
        "unit_amount_decimal": price.unit_amount,
        "currency": price.currency,
        "product": price.product,
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


def create_gift(
    gift_giver_subscription: djstripe.models.Subscription, user
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
                }
            )

    args = dict(
        customer=user.stripe_customer.id,
        items=items,
        # cancel_at=(datetime.now() - relativedelta(days=1)) + relativedelta(months=promo_code.coupon.duration_in_months),
        promotion_code=promo_code_id,
        payment_behavior="allow_incomplete",
        collection_method="send_invoice",
        off_session=True,
        metadata={
            "gift_giver_subscription": gift_giver_subscription.id,
            "promo_code": promo_code_id,
        },
    )
    subscription = stripe.Subscription.create(**args)

    djstripe.models.Subscription.sync_from_stripe_data(subscription)
    user.refresh_stripe_data()


def get_primary_product_for_djstripe_subscription(sub):
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
