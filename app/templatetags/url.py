from urllib import parse

from django import template
from django.http.request import HttpRequest

register = template.Library()


@register.simple_tag(takes_context=True)
def qs_link(context, base_url=None, **kwargs):
    """
    Add query kwargs to URL
    """
    request: HttpRequest = context.get("request", None)
    if request is None:
        return

    params = request.GET.dict()
    if base_url is not None:
        params.update(parse.parse_qs(parse.urlsplit(base_url).query))

    for key, value in kwargs.items():
        if value is None or not value:
            params.pop(key, None)
        else:
            params[key] = value

    return (base_url if base_url is not None else "") + "?" + parse.urlencode(params)


@register.simple_tag(takes_context=True)
def url_test(context, includes, **kwargs):
    request: HttpRequest = context.get("request", None)
    if request is None:
        return
    url = request.get_full_path()
    return includes in url
