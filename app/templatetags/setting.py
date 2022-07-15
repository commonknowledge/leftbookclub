import json
import urllib.parse

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

@register.simple_tag(takes_context=True)
def oauth_application_from_query(context):
    try:
        request = context["request"]
        print("request.GET", request.GET)
        next = request.GET.get('next', None)
        print("next", next)
        if next is not None:
            next_url_parts = urllib.parse.urlparse(next)
            print("next_url_parts", next_url_parts)
            print("next_url_parts.query", next_url_parts.query)
            client_id = next_url_parts.query.get('client_id', None)
            if client_id is not None:
                app = OAuthApp.filter(client_id=client_id).first()
                return app
    except:
        return None
