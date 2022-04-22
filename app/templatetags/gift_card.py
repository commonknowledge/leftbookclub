from django import template
from django.template.loader import render_to_string

from app.utils.stripe import (
    gift_giver_subscription_from_code,
    is_real_gift_code,
    is_redeemable_gift_code,
    subscription_with_promocode,
)

register = template.Library()


@register.simple_tag
def gift_card_from_code(code):
    return render_to_string(
        "app/includes/gift_card.html",
        context={"code": code, "subscription": gift_giver_subscription_from_code(code)},
    )


@register.filter
def is_real_gift_card(code):
    return is_real_gift_code(code)


@register.filter
def is_redeemable_gift_card(code):
    return is_redeemable_gift_code(code)


@register.filter
def with_gift_code(self):
    return subscription_with_promocode(self)
