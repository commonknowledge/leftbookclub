import djstripe.models
import stripe
from django.db import models
from djstripe.enums import SubscriptionStatus

from app.models.django import User
from app.utils.stripe import (
    configure_gift_giver_subscription_and_code,
    create_gift_recipient_subscription,
)


class LegacyGifts(models.Model):
    """
    Generated from SQL query on data dump:

        SELECT
            g.id as "gift_id",
            g.code as "gift_code",
            us.user_id as "giving_user",
            gifters.email as "giving_user_email",
            giftsub.stripe_id as "giving_sub",
        --  giftsub.stripe_status as "giving_stripe_status",
            g.email as "initial_recipient_email",
            recipients.id as "recipient_user_matching_gift_email",
        --  recipientsub.stripe_id as "follow_up_recipient_sub",
        --  recipientsub.stripe_status
        FROM gifts g
        LEFT JOIN user_subscription us ON us.id = g.user_subscription_id
        LEFT JOIN users recipients ON recipients.email = g.email
        LEFT JOIN users gifters ON gifters.id = us.user_id
        LEFT JOIN subscriptions giftsub ON giftsub.user_id = us.user_id
        LEFT JOIN subscriptions recipientsub ON recipientsub.user_id = recipients.id
        ORDER BY giftsub.stripe_status, g.id;
    """

    gift_id = models.CharField(max_length=500, unique=True)
    gift_code = models.CharField(max_length=500, blank=True)
    giving_user = models.ForeignKey(
        User,
        to_field="old_id",
        null=False,
        blank=False,
        related_name="legacy_gifts_given",
        on_delete=models.DO_NOTHING,
    )
    giving_user_email = models.CharField(max_length=500, blank=True)
    giving_sub = models.ForeignKey(
        djstripe.models.Subscription,
        to_field="id",
        null=False,
        blank=False,
        related_name="legacy_gift_record",
        on_delete=models.DO_NOTHING,
    )
    # giving_stripe_status = models.CharField(max_length=500, blank=True)
    initial_recipient_email = models.CharField(max_length=500, blank=True)
    recipient_user_matching_gift_email = models.ForeignKey(
        User,
        to_field="old_id",
        null=True,
        blank=True,
        related_name="legacy_gifts_received",
        on_delete=models.DO_NOTHING,
    )
    # follow_up_recipient_sub = models.ForeignKey(djstripe.models.Subscription, to_field='id', null=True, blank=True, on_delete=models.DO_NOTHING)
    # stripe_status = models.CharField(max_length=500, blank=True)
    migrated = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.migrated is False:
            migration_breadcrumb_metadata = {
                "legacy_gift_django_id": self.id,
                "legacy_gift_id": self.gift_id,
            }
            # Only proceed if the gift giver subscription is active
            giving_sub = stripe.Subscription.retrieve(self.giving_sub.id)
            self.giving_sub.sync_from_stripe_data(giving_sub)
            if self.giving_sub != SubscriptionStatus.canceled:
                # Convert gift codes into promotion codes and mark the gift giver subscriptions with the relevant metadata (gift_mode=True, promo_code=X)
                details = configure_gift_giver_subscription_and_code(
                    self.giving_sub.id,
                    self.giving_user.id,
                    metadata=migration_breadcrumb_metadata,
                )
                # Check for where a recipient user exists + the recipient user doesn't already have a non-gift_mode subscription
                if (
                    self.recipient_user_matching_gift_email is not None
                    and self.recipient_user_matching_gift_email.active_subscription
                    is None
                ):
                    # If true, then create a gift recipient subscription for the recipient using this promo code modelled on the giver subscription with relevant metadata
                    create_gift_recipient_subscription(
                        details["gift_giver_subscription"],
                        self.recipient_user_matching_gift_email,
                        metadata=migration_breadcrumb_metadata,
                    )
                self.migrated = True
        super().save(*args, **kwargs)
