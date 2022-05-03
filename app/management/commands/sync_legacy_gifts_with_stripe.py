import djstripe.models
import stripe
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.functions import Length
from djstripe.enums import SubscriptionStatus

from app.models.django import User
from app.models.legacy import LegacyGifts
from app.utils.stripe import (
    configure_gift_giver_subscription_and_code,
    create_gift_recipient_subscription,
)


class Command(BaseCommand):
    help = "Create BookPage for each Shopify product"

    def add_arguments(self, parser):
        parser.add_argument(
            "-b", "--batch", dest="batch_size", type=int, default=100000
        )

    def legacy_data_to_stripe_address(self, user):
        return {
            "line1": user.address1,
            "line2": user.address2,
            "postal_code": user.postcode,
            "city": user.city,
            "state": user.state,
            "country": user.country,
        }

    def handle(self, *args, **options):
        batch_size = options.get("batch_size")
        legacy_gifts = LegacyGifts.objects.filter(migrated=False).all()[:batch_size]
        print("Syncing legacy gifts", len(legacy_gifts))
        for gift in legacy_gifts:
            if gift.migrated is False:
                migration_breadcrumb_metadata = {
                    "legacy_gift_django_id": gift.id,
                    "legacy_gift_id": gift.gift_id,
                }
                # Only proceed if the gift giver subscription is active
                giving_sub = stripe.Subscription.retrieve(gift.giving_sub)
                giving_sub = djstripe.models.Subscription.sync_from_stripe_data(
                    giving_sub
                )
                if giving_sub.status != SubscriptionStatus.canceled:
                    giving_user = User.objects.get(old_id=gift.giving_user)
                    # Convert gift codes into promotion codes and mark the gift giver subscriptions with the relevant metadata (gift_mode=True, promo_code=X)
                    (
                        promo_code,
                        gift_giver_subscription,
                    ) = configure_gift_giver_subscription_and_code(
                        giving_sub.id,
                        giving_user.id,
                        metadata=migration_breadcrumb_metadata,
                        code=gift.gift_code,
                    )
                    # Check for where a recipient user exists + the recipient user doesn't already have a non-gift_mode subscription
                    if gift.recipient_user_matching_gift_email is not None:
                        recipient = User.objects.get(
                            old_id=gift.recipient_user_matching_gift_email
                        )
                        if recipient.active_subscription is None:
                            # If true, then create a gift recipient subscription for the recipient using this promo code modelled on the giver subscription with relevant metadata
                            create_gift_recipient_subscription(
                                gift_giver_subscription,
                                recipient,
                                metadata=migration_breadcrumb_metadata,
                            )
                    gift.migrated = True
                    gift.save()
