from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtailautocomplete.urls.admin import urlpatterns as autocomplete_admin_urls

from app.views import ShippingCostView, StripeCustomerPortalView

# from wagtail_transfer import urls as wagtailtransfer_urls


urlpatterns = [
    path("django/", admin.site.urls),
    re_path(r"^admin/autocomplete/", include(autocomplete_admin_urls)),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/images/logo.png", permanent=True),
    ),
    path(
        "accounts/membership/",
        TemplateView.as_view(template_name="account/membership.html"),
        name="account_membership",
    ),
    path("accounts/", include("allauth.urls")),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path("customer_portal/", StripeCustomerPortalView.as_view(), name="customerportal"),
    path(
        ShippingCostView.url_pattern, ShippingCostView.as_view(), name="shippingcosts"
    ),
    # re_path(r'^wagtail-transfer/', include(wagtailtransfer_urls)),
    # For anything not caught by a more specific rule above, hand over to Wagtail's serving mechanism
    re_path(r"", include(wagtail_urls)),
]

if settings.DEBUG:
    if settings.USE_DEBUG_TOOLBAR:
        import debug_toolbar

        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
