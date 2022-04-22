from django import template

from app.models.stripe import subscription_with_promocode

register = template.Library()


@register.filter
def with_gift_code(self):
    return subscription_with_promocode(self)
