from django import template

from app.models.wagtail import BookPage

register = template.Library()


@register.simple_tag
def get_books(since=None):
    qs = BookPage.objects.live().filter(published_date__isnull=False)
    if since:
        qs = qs.filter(published_date__gte=since)
    products = [
        {
            "page": p,
            "product": p.shopify_product,
            "metafields": p.shopify_product_metafields,
        }
        for p in qs.order_by("-published_date")
    ]
    return products
