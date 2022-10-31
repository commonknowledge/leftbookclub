from django import template

from app.models.wagtail import BookPage

register = template.Library()


@register.simple_tag
def get_books(since=None, types=None):
    qs = (
        BookPage.objects.live()
        .public()
        .order_by("-published_date")
        .filter(published_date__isnull=False)
    )
    if since:
        qs = qs.filter(published_date__gte=since)
    if types and len(types) > 0:
        qs = qs.filter(type__in=types)
    return qs
