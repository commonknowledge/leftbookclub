import posthog
from django.conf import settings


def posthog_event_properties():
    return {
        "environment": settings.FLY_APP_NAME,
        "debug": settings.DEBUG,
        "base_url": settings.BASE_URL,
    }


def identify_user(user):
    if user is None:
        return

    data = user.get_analytics_data()
    posthog.identify(user.id, data.set)

    if user.primary_email is not None:
        posthog.alias(user.primary_email, user.id)

    if user.stripe_customer is not None:
        posthog.alias(user.stripe_customer.id, user.id)


def signup(user):
    identify_user(user)
    posthog.capture(user.id, event="user signup", properties=posthog_event_properties())


def redeem(user):
    identify_user(user)
    posthog.capture(user.id, event="redeem", properties=posthog_event_properties())


def buy_book(user):
    identify_user(user)
    posthog.capture(user.id, event="buy book", properties=posthog_event_properties())


def buy_gift(user):
    identify_user(user)
    posthog.capture(user.id, event="buy gift", properties=posthog_event_properties())


def visit_stripe_checkout(user):
    identify_user(user)
    posthog.capture(
        user.id,
        event="$pageview stripe checkout",
        properties=posthog_event_properties(),
    )


def visit_stripe_customerportal(user):
    identify_user(user)
    posthog.capture(
        user.id,
        event="$pageview stripe customerportal",
        properties=posthog_event_properties(),
    )


def buy_membership(user):
    identify_user(user)
    posthog.capture(
        user.id, event="buy membership", properties=posthog_event_properties()
    )


def manage_subscription(user):
    identify_user(user)
    posthog.capture(
        user.id, event="manage subscription", properties=posthog_event_properties()
    )


def cancel_membership(user):
    identify_user(user)
    posthog.capture(
        user.id, event="cancel membership", properties=posthog_event_properties()
    )


def cancel_gift_card(user):
    identify_user(user)
    posthog.capture(user.id, event="cancel gift", properties=posthog_event_properties())
