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
        user_data = request.user.get_analytics_data()

    return {"user_data": mark_safe(json.dumps(user_data))}
