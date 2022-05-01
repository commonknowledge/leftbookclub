from django.conf import settings


def update_stripe_customer_subscription(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        if not request.path.startswith(settings.STATIC_URL):
            # Code to be executed for each request before
            # the view (and later middleware) are called.
            if request.user.is_authenticated:
                request.user.refresh_stripe_data()

        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware
