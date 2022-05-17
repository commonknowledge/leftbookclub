from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.templatetags.static import static as get_static_path
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from shopify_webhook.views import WebhookView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail_transfer import urls as wagtailtransfer_urls
from wagtailautocomplete.urls.admin import urlpatterns as autocomplete_admin_urls

from app.views import (
    CancellationView,
    CartOptionsView,
    CompletedGiftPurchaseView,
    CompletedGiftRedemptionView,
    CompletedMembershipPurchaseView,
    GiftCodeRedeemView,
    GiftMembershipSetupView,
    LoginRequiredTemplateView,
    ShippingCostView,
    ShippingForProductView,
    StripeCheckoutSuccessView,
    StripeCustomerPortalView,
    SubscriptionCheckoutView,
)

# from wagtail_transfer import urls as wagtailtransfer_urls


urlpatterns = [
    path("django/", admin.site.urls),
    re_path(r"^admin/autocomplete/", include(autocomplete_admin_urls)),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    re_path(r"^wagtail-transfer/", include(wagtailtransfer_urls)),
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
        "accounts/cancel/<str:subscription_id>",
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
        f"redeem/<str:code>/",
        GiftCodeRedeemView.as_view(),
        name="redeem",
    ),
    path(
        "welcome/",
        CompletedMembershipPurchaseView.as_view(),
        name="completed_membership_purchase",
    ),
    path(
        "gift/redeemed/",
        CompletedGiftRedemptionView.as_view(),
        name="completed_gift_redemption",
    ),
    path(
        "gift/bought/",
        CompletedGiftPurchaseView.as_view(),
        name="completed_gift_purchase",
    ),
    path(
        f"checkout/success/",
        StripeCheckoutSuccessView.as_view(),
        name="stripe_checkout_success",
    ),
    path(
        f"checkout/{SubscriptionCheckoutView.url_params}",
        SubscriptionCheckoutView.as_view(),
        name="stripe_checkout",
    ),
    path(
        f"confirm-shipping/{ShippingForProductView.url_params[0]}",
        ShippingForProductView.as_view(),
        name="plan_shipping",
    ),
    path(
        f"confirm-shipping/{ShippingForProductView.url_params[1]}",
        ShippingForProductView.as_view(),
        name="plan_shipping",
    ),
    path("accounts/", include("allauth.urls")),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path("customer_portal/", StripeCustomerPortalView.as_view(), name="customerportal"),
    path("shopify/webhook/", WebhookView.as_view(), name="shopify_webhook"),
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
