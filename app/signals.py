import stripe
from djstripe import webhooks

from app.utils.stripe import gift_recipient_subscription_from_code


@webhooks.handler("customer.subscription.deleted")
def cancel_gift_recipient_subscription(event, **kwargs):
    # update their situation on mailchimp
    object = event.data.get("object", {})
    if (
        object.get("object", None) == "subscription"
        and object.get("metadata", {}).get("gift_mode", None) is not None
    ):
        promo_code = object.get("metadata", {}).get("promo_code", None)
        recipient_subscription = gift_recipient_subscription_from_code(promo_code)
        stripe.Subscription.delete(recipient_subscription.id)
        # TODO: send them an email
        # update their situation on mailchimp
