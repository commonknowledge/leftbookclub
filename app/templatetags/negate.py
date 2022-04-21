from django import template
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from djstripe.utils import CURRENCY_SIGILS

register = template.Library()


@register.filter
def negate(b):
    return not b
