from datetime import date, datetime

import pytz
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from django import template
from django.utils.translation import gettext_lazy as _

utc = pytz.UTC

register = template.Library()


@register.filter
def to_date(self):
    if isinstance(self, date) or isinstance(self, datetime):
        return self
    return parse(self)


@register.simple_tag
def adjust_date(date, key, value):
    return date + relativedelta(**{key: value})


@register.simple_tag
def date_is_later_than(date, compare_date):
    return format_date(date) > format_date(compare_date)


def format_date(date):
    return parse(str(date)).replace(tzinfo=None)
