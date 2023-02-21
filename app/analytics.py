from typing import Optional

import posthog
from django.conf import settings

from app.apps import basic_posthog_event_properties
from app.models import User
from app.utils.mailchimp import track_event_for_user_in_mailchimp


def identify_user(user):
    if user is None:
        return

    data = user.get_analytics_data()
    posthog.identify(user.id, data["set"])

    if user.primary_email is not None:
        posthog.alias(user.primary_email, user.id)

    if user.stripe_customer is not None:
        posthog.alias(user.stripe_customer.id, user.id)


def capture_posthog_event(user: User, event: str, properties=dict()):
    identify_user(user)
    data = basic_posthog_event_properties
    if hasattr(user, "get_analytics_data"):
        data.update(user.get_analytics_data().get("register", {}))
    data.update(properties)
    posthog.capture(user.id, event=event, properties=data)


def signup(user):
    capture_posthog_event(user, event="user signup")
    track_event_for_user_in_mailchimp(user, "membership_signup")


def redeem(user):
    capture_posthog_event(user, event="redeem")
    track_event_for_user_in_mailchimp(user, "redeem_gift_card")


def donate(user, new_amount: float, old_amount: Optional[float] = None):
    props = {"old_amount": old_amount, "new_amount": new_amount}
    capture_posthog_event(user, event="add recurring donation", properties=props)
    track_event_for_user_in_mailchimp(user, "add_recurring_donation", properties=props)


def donation_ended(user, old_amount: Optional[float] = None):
    props = {"old_amount": old_amount}
    capture_posthog_event(user, event="donation ended", properties=props)
    track_event_for_user_in_mailchimp(user, "donation_ended", properties=props)


def upgrade_remain_on_current_plan(
    user,
    old_amount,
    old_plan,
    old_product,
    old_interval,
    old_interval_count,
    campaign=None,
):
    props = {
        "campaign": str(campaign),
        "old_amount": old_amount,
        "old_plan": str(old_plan),
        "old_product": str(old_product),
        "old_interval": str(old_interval),
        "old_interval_count": old_interval_count,
    }
    capture_posthog_event(user, event="decline upgrade request", properties=props)
    track_event_for_user_in_mailchimp(user, "decline_upgrade_request", properties=props)


def upgrade(
    user,
    option_title,
    old_amount,
    new_amount,
    old_plan,
    new_plan,
    old_product,
    new_product,
    old_interval,
    new_interval,
    old_interval_count,
    new_interval_count,
    campaign=None,
):
    props = {
        "option_title": str(option_title),
        "campaign": str(campaign),
        "old_amount": old_amount,
        "new_amount": new_amount,
        "old_discount_percent": (new_amount - old_amount) / new_amount,
        "amount_increase": new_amount - old_amount,
        "amount_increase_percent": (new_amount - old_amount) / old_amount,
        "old_plan": str(old_plan),
        "new_plan": str(new_plan),
        "old_product": str(old_product),
        "new_product": str(new_product),
        "old_interval": str(old_interval),
        "new_interval": str(new_interval),
        "old_interval_count": old_interval_count,
        "new_interval_count": new_interval_count,
    }
    capture_posthog_event(user, event="upgrade membership", properties=props)
    track_event_for_user_in_mailchimp(user, "upgrade_membership", props)


def buy_book(user):
    capture_posthog_event(user, event="buy book")
    track_event_for_user_in_mailchimp(user, "buy_book")


def buy_gift(user):
    capture_posthog_event(user, event="buy gift")
    track_event_for_user_in_mailchimp(user, "buy_gift")


def visit_stripe_checkout(user):
    capture_posthog_event(user, event="$pageview stripe checkout")
    track_event_for_user_in_mailchimp(user, "visit_stripe_checkout")


def visit_stripe_customerportal(user):
    capture_posthog_event(user, event="$pageview stripe customerportal")
    track_event_for_user_in_mailchimp(user, "visit_stripe_customerportal")


def buy_membership(user):
    capture_posthog_event(user, event="buy membership")
    track_event_for_user_in_mailchimp(user, "buy_membership")


def manage_subscription(user):
    capture_posthog_event(user, event="manage subscription")
    track_event_for_user_in_mailchimp(user, "manage_subscription")


def cancel_membership(user):
    capture_posthog_event(user.id, event="cancel_membership")
    track_event_for_user_in_mailchimp(user, "cancel membership")


def expire_membership(user):
    capture_posthog_event(user, event="expired membership")
    track_event_for_user_in_mailchimp(user, "expire_membership")


def cancel_gift_card(user):
    capture_posthog_event(user, event="cancel gift")
    track_event_for_user_in_mailchimp(user, "cancel_gift")
