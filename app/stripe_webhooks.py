import stripe
from djstripe import webhooks

from app.utils.stripe import gift_recipient_subscription_from_code


@webhooks.handler("customer.subscription.deleted")
def gift_giver_subscription_was_cancelled(event, **kwargs):
    some_subscription = event.data.object
    if some_subscription.metadata.get("gift_mode", None) is not None:
        promo_code = some_subscription.metadata.get("promo_code", None)
        recipient_subscription = gift_recipient_subscription_from_code(promo_code)
        stripe.Subcription.delete(recipient_subscription.id)
