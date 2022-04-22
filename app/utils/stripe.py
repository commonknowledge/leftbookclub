from typing import Union

from datetime import datetime

import djstripe.models
import stripe
from dateutil.relativedelta import relativedelta


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


def subscription_with_promocode(
    sub: Union[stripe.Subscription, djstripe.models.Subscription]
):
    promo_code_id = sub.metadata.get("promo_code", None)
    if promo_code_id is not None:
        promocode = stripe.PromotionCode.retrieve(promo_code_id)
        setattr(sub, "promo_code", promocode)
    return sub


def create_gift(
    gift_giver_subscription: djstripe.models.Subscription, user
) -> djstripe.models.Subscription:
    if user.stripe_customer is None:
        djstripe.models.Customer.create(user)

    # Get number of months from gift_giver_subscription.metadata.get('promo_code_id') -> pc.coupon.duration_in_months
    promo_code_id = gift_giver_subscription.metadata.get("promo_code")
    # promo_code = stripe.PromotionCode.retrieve(promo_code_id)

    args = dict(
        customer=user.stripe_customer.id,
        items=[
            {"price": si.price.id, "quantity": si.quantity}
            for si in gift_giver_subscription.items.all()
        ],
        # cancel_at=(datetime.now() - relativedelta(days=1)) + relativedelta(months=promo_code.coupon.duration_in_months),
        promotion_code=promo_code_id,
        payment_behavior="allow_incomplete",
        metadata={
            "gift_giver_subscription": gift_giver_subscription.id,
            "promo_code": promo_code_id,
        },
    )
    subscription = stripe.Subscription.create(**args)

    djstripe.models.Subscription.sync_from_stripe_data(subscription)
    user.refresh_stripe_data()
