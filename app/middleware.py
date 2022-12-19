from django.conf import settings


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
