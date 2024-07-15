from django import template

from app.models.wagtail import BookPage, MerchandisePage
from app.utils import ensure_list

register = template.Library()


@register.simple_tag
def get_books(since=None, types=None, limit=None):
    qs = (
        BookPage.objects.live()
        .public()
        .order_by("-published_date")
        .filter(published_date__isnull=False)
    )
    if since:
        qs = qs.filter(published_date__gte=since)
    if types is not None:
        types = ensure_list(types)
        if len(types) > 0 and "all-books" not in types:
            qs = qs.filter(type__in=types)
    if limit:
        qs = qs[:limit]
    return qs


@register.simple_tag
def get_merch():
    return MerchandisePage.objects.live().public()

@register.filter(name='strikethrough')
def strikethrough(text):
    """Convert text to strikethrough using Unicode characters."""
    return ''.join(char + '\u0336' for char in str(text))