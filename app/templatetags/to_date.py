from dateutil.parser import parse
from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def to_date(self):
    return parse(self)
