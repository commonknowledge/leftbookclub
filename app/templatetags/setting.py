import json

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.simple_tag
def setting(name, default=None):
    try:
        value = getattr(settings, name)
        return value
    except:
        return default


@register.inclusion_tag("app/includes/user_data.html", takes_context=True)
def user_data(context):
    request = context["request"]

    user_data = {
        "is_authenticated": False,
    }

    if request.user.is_authenticated:
        user_data = {
            "is_authenticated": True,
            "id": request.user.id,
            "email": request.user.email,
            "name": request.user.get_full_name(),
            "stripe_customer_id": request.user.stripe_customer.id,
        }

        if not settings.STRIPE_LIVE_MODE:
            user_data["id"] = f"{request.user.id}-{request.get_host()}"

    return {"user_data": mark_safe(json.dumps(user_data))}
