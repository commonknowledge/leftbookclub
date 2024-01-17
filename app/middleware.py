import json
from urllib.parse import unquote

import posthog
from django.conf import settings


def frontend_backend_posthog_identity_linking(get_response):
    def middleware(request):
        posthog_cookie = request.COOKIES.get(f"ph_{posthog.project_api_key}_posthog")
        if posthog_cookie:
            cookie_dict = json.loads(unquote(posthog_cookie))
            if cookie_dict["distinct_id"] and request.user.is_authenticated:
                posthog.alias(cookie_dict["distinct_id"], request.user.primary_email)

        if request.session.session_key is not None and request.user.is_authenticated:
            posthog.alias(request.session.session_key, request.user.primary_email)
            posthog.alias(request.session.session_key, request.user.id)

        response = get_response(request)

        return response

    return middleware


def update_stripe_customer_subscription(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        stripeless_request = (
            request.path.startswith(settings.STATIC_URL)
            or request.path.startswith(settings.MEDIA_URL)
            or request.path.startswith("/anonymous/")
            or settings.SHOPIFY_WEBHOOK_PATH in request.path
            or settings.SHOPIFY_WEBHOOK_PATH == request.path
            or request.path.startswith("/admin/")
            or request.path.startswith("/django/")
            or request.path.startswith("/oauth/")
            or request.path.startswith("/documents/")
            or request.path.startswith("/silk/")
            or request.path.startswith("/__debug__/")
            or "favicon.ico" in request.path
        )

        if not stripeless_request:
            # Code to be executed for each request before
            # the view (and later middleware) are called.
            if request.user.is_authenticated:
                request.user.refresh_stripe_data()

        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware
