from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.templatetags.static import static as get_static_path
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtailautocomplete.urls.admin import urlpatterns as autocomplete_admin_urls

from app.shopify_webhook.views import WebhookView
from app.views import (
    CancellationView,
    CartOptionsView,
    GiftCodeRedeemView,
    GiftMembershipSetupView,
    LoginRequiredTemplateView,
    MemberSignupCompleteView,
    ShippingCostView,
    ShippingForProductView,
    StripeCustomerPortalView,
    SubscriptionCheckoutView,
)

# from wagtail_transfer import urls as wagtailtransfer_urls


urlpatterns = [
    path("django/", admin.site.urls),
    re_path(r"^admin/autocomplete/", include(autocomplete_admin_urls)),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path(
        "favicon.ico",
        RedirectView.as_view(url=get_static_path("images/logo.png"), permanent=True),
    ),
    path(
        "accounts/profile/",
        LoginRequiredTemplateView.as_view(template_name="account/membership.html"),
        name="account_membership",
    ),
    path(
        "accounts/billing-and-shipping/",
        LoginRequiredTemplateView.as_view(template_name="account/billing.html"),
        name="billing_shipping",
    ),
    path(
        "accounts/gift-cards/",
        LoginRequiredTemplateView.as_view(template_name="account/gifts.html"),
        name="gift_cards",
    ),
    path(
        "accounts/cancel/",
        CancellationView.as_view(),
        name="cancel_membership",
    ),
    path(
        "redeem/",
        GiftCodeRedeemView.as_view(),
        name="redeem",
    ),
    path(
        "redeem/setup/",
        GiftMembershipSetupView.as_view(),
        name="redeem_setup",
    ),
    path(
        "welcome/",
        MemberSignupCompleteView.as_view(),
        name="member_signup_complete",
    ),
    path(
        "redeem/<str:code>/",
        GiftCodeRedeemView.as_view(),
        name="redeem",
    ),
    path("checkout/<product_id>/", SubscriptionCheckoutView.as_view(), name="checkout"),
    path(
        "product/<product_id>/",
        ShippingForProductView.as_view(),
        name="shipping_for_product",
    ),
    path(
        "product/<product_id>/<country_id>/",
        ShippingForProductView.as_view(),
        name="shipping_for_product",
    ),
    path("accounts/", include("allauth.urls")),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path("customer_portal/", StripeCustomerPortalView.as_view(), name="customerportal"),
    path("webhooks/shopify/", WebhookView.as_view(), name="shopify_webhook"),
    path(
        ShippingCostView.url_pattern, ShippingCostView.as_view(), name="shippingcosts"
    ),
    path(CartOptionsView.url_pattern, CartOptionsView.as_view(), name="cartoptions"),
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
