import logging

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.templatetags.static import static as get_static_path
from django.urls import include, path, re_path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from shopify_webhook.views import WebhookView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail_transfer import urls as wagtailtransfer_urls
from wagtailautocomplete.urls.admin import urlpatterns as autocomplete_admin_urls

from app import views
from app.views import (
    BatchUpdateSubscriptionsStatusView,
    BatchUpdateSubscriptionsView,
    CancellationView,
    CartOptionsView,
    CompletedGiftPurchaseView,
    CompletedGiftRedemptionView,
    CompletedMembershipPurchaseView,
    DonationView,
    GiftCodeRedeemView,
    GiftMembershipSetupView,
    LoginRequiredTemplateView,
    ProductRedirectView,
    RefreshDataView,
    ShippingCostView,
    ShippingForProductView,
    StripeCheckoutSuccessView,
    StripeCustomerPortalView,
    SubscriptionCheckoutView,
    SyncShopifyWebhookEndpoint,
    UpgradeSuccessDonationTrailerView,
    UpgradeView,
    WagtailStreamfieldBlockTurboFrame,
)

urlpatterns = [
    path("oauth/", include("oauth2_provider.urls", namespace="oauth2_provider")),
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
        "accounts/cancel/<str:subscription_id>/",
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
        f"update-membership/",
        UpgradeView.as_view(),
        name="upgrade",
    ),
    path(
        f"update-membership/success/",
        UpgradeSuccessDonationTrailerView.as_view(),
        name="upgrade-success",
    ),
    path(
        f"donate/",
        DonationView.as_view(),
        name="donate",
    ),
    path(
        f"donate/success/",
        LoginRequiredTemplateView.as_view(template_name="app/donate_success.html"),
        name="donation-success",
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
    path(
        f"refresh/",
        RefreshDataView.as_view(),
        name="refresh_circle",
    ),
    path(
        "batch-update-subscriptions/",
        BatchUpdateSubscriptionsView.as_view(),
        name="batch_update_subscriptions",
    ),
    path(
        "batch-update-subscriptions/status/<str:batch_id>/",
        BatchUpdateSubscriptionsStatusView.as_view(),
        name="batch_update_subscriptions_batch_status",
    ),
    ### V2 signup flow
    # CreateMembershipView
    # SelectReadingSpeedView
    # SelectSyllabusView
    # SelectShippingCountryView
    # SelectBillingPlanView
    # SelectDonationView
    # V2SubscriptionCheckoutView
    path(
        "signup/",
        views.CreateMembershipView.as_view(),
        name="signup",
    ),
    path(
        "signup/reading-speed/",
        views.SelectReadingSpeedView.as_view(),
        name="signup_reading_speed",
    ),
    path(
        "signup/syllabus/",
        views.SelectSyllabusView.as_view(),
        name="signup_syllabus",
    ),
    path(
        "signup/shipping/",
        views.SelectShippingCountryView.as_view(),
        name="signup_shipping",
    ),
    path(
        "signup/billing/",
        views.SelectBillingPlanView.as_view(),
        name="signup_billing",
    ),
    path(
        "signup/donation/",
        views.SelectDonationView.as_view(),
        name="signup_donation",
    ),
    path(
        "signup/checkout/",
        views.V2SubscriptionCheckoutView.as_view(),
        name="v2_stripe_checkout",
    ),
    ### END V2 signup flow
    ###
    path("accounts/", include("allauth.urls")),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path("customer_portal/", StripeCustomerPortalView.as_view(), name="customerportal"),
    path(settings.SHOPIFY_WEBHOOK_PATH, WebhookView.as_view(), name="shopify_webhook"),
    path(
        ShippingCostView.url_pattern, ShippingCostView.as_view(), name="shippingcosts"
    ),
    path(CartOptionsView.url_pattern, CartOptionsView.as_view(), name="cartoptions"),
    path("anonymous/product/<int:id>/", ProductRedirectView.as_view(), name="product"),
    path(settings.SYNC_SHOPIFY_WEBHOOK_ENDPOINT, SyncShopifyWebhookEndpoint.as_view()),
    path(
        "anonymous/frames/all_merch/",
        TemplateView.as_view(template_name="app/frames/all_merch.html"),
        name="all_merch",
    ),
    path(
        "anonymous/frames/all_books/",
        TemplateView.as_view(template_name="app/frames/all_books.html"),
        name="all_books",
    ),
    path(
        "anonymous/frames/membership_options_grid/<int:page_id>/<str:field_name>/<str:block_id>/",
        WagtailStreamfieldBlockTurboFrame.as_view(
            template_name="app/frames/membership_options_grid.html"
        ),
        name="membership_options_grid",
    ),
    path("geo/postcode/<str:postcode>/", views.postcode_lookup_view, name="postcode_lookup"),

    # re_path(r'^wagtail-transfer/', include(wagtailtransfer_urls)),
    # For anything not caught by a more specific rule above, hand over to Wagtail's serving mechanism
]

if settings.USE_SILK:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

if settings.DEBUG:
    if settings.USE_DEBUG_TOOLBAR:
        import debug_toolbar

        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r"", include(wagtail_urls)),
]
