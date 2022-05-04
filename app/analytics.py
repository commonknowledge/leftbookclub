import posthog


def identify_user(user):
    if user is None:
        return

    posthog.identify(
        user.id,
        {"email": user.email, "name": user.get_full_name(), "staff": user.is_staff},
    )
    if user.stripe_customer is not None:
        posthog.alias(user.stripe_customer.id, user.id)
    if user.old_id is not None:
        posthog.alias(f"old-{user.old_id}", user.id)


def signup(user):
    identify_user(user)
    posthog.capture(user.id, event="user signup")


def redeem(user):
    identify_user(user)
    posthog.capture(user.id, event="redeem")


def buy_book(user):
    identify_user(user)
    posthog.capture(user.id, event="buy book")


def buy_gift(user):
    identify_user(user)
    posthog.capture(user.id, event="buy gift")


def buy_membership(user):
    identify_user(user)
    posthog.capture(user.id, event="buy membership")


def manage_subscription(user):
    identify_user(user)
    posthog.capture(user.id, event="manage subscription")


def cancel_membership(user):
    identify_user(user)
    posthog.capture(user.id, event="cancel membership")


def cancel_gift_card(user):
    identify_user(user)
    posthog.capture(user.id, event="cancel gift")
