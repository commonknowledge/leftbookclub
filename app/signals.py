import stripe
from djstripe import webhooks

from app.utils.stripe import gift_recipient_subscription_from_code


@webhooks.handler("customer.subscription.deleted")
def cancel_gift_recipient_subscription(event, **kwargs):
    # update their situation on mailchimp
    if (
        event.subscription is not None
        and event.subscription.metadata.get("gift_mode", None) is not None
    ):
        promo_code = event.subscription.metadata.get("promo_code", None)
        recipient_subscription = gift_recipient_subscription_from_code(promo_code)
        stripe.Subcription.delete(recipient_subscription.id)
        # TODO: send them an email
        # update their situation on mailchimp
