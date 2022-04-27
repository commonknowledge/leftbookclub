import posthog


def identify_user(user):
    if user is None:
        return

    posthog.identify(user.id, {"email": user.email, "name": user.get_full_name()})


def signup(user):
    identify_user(user)
    posthog.capture(user.id, event="user signup")


def redeem(user):
    identify_user(user)
    posthog.capture(user.id, event="redeem")


def buy_book(user):
    identify_user(user)
    posthog.capture(user.id, event="buy book")


def manage_subscription(user):
    identify_user(user)
    posthog.capture(user.id, event="manage subscription")


def cancel_subscription(user):
    identify_user(user)
    posthog.capture(user.id, event="cancel subscription")
