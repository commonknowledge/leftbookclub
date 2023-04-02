import shopify
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import BookPage
from app.models.wagtail import MerchandisePage


class Command(BaseCommand):
    help = "Update subscription"

    def add_arguments(self, parser):
        parser.add_argument(
            "--subscription_id",
            dest="subscription_id",
            help="Stripe subscription ID",
        )
        parser.add_argument(
            "--add_or_update_shipping",
            dest="add_or_update_shipping",
            default=False,
            help="Add or update shipping",
        )
        parser.add_argument(
            "--optional_custom_shipping_fee",
            dest="optional_custom_shipping_fee",
            default=False,
            help="Defaults to the system shipping fee for the customer's country.",
        )
        parser.add_argument(
            "--update_membership_fee",
            dest="update_membership_fee",
            default=False,
            help="Update membership fee",
        )
        parser.add_argument(
            "--optional_custom_membership_fee",
            dest="optional_custom_membership_fee",
            default=False,
            help="Defaults to the current price of the customer's membership plan.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        run(**options)


import djstripe.models
import stripe


def run(
    subscription_id: str,
    proration_behaviour: str = "none",
    add_or_update_shipping=False,
    optional_custom_shipping_fee=None,
    update_membership_fee=False,
    optional_custom_membership_fee=None,
):
    #### Validate user
    user = djstripe.models.Subscription.objects.get(
        id=subscription_id
    ).customer.subscriber

    if (
        user.active_subscription is None
        or user.active_subscription.membership_plan_price is None
        or user.active_subscription.membership_si is None
        or user.active_subscription.is_gift_receiver
    ):
        raise ValueError("User is not a member.")

    #### Create line items

    line_items = []

    if update_membership_fee:
        # Create new membership item
        line_items += [
            {
                "price_data": user.active_subscription.membership_plan_price.to_price_data(
                    product=user.active_subscription.membership_si.plan.product,
                    amount=optional_custom_membership_fee,
                ),
                "quantity": 1,
            }
        ]
        # Replace old membership item
        line_items += [
            {"id": user.active_subscription.membership_si.id, "deleted": True}
        ]

    if add_or_update_shipping:
        # Create new shipping item
        line_items += [
            {
                "price_data": user.active_subscription.membership_plan_price.to_shipping_price_data(
                    zone=user.active_subscription.shipping_zone,
                    amount=optional_custom_shipping_fee,
                ),
                "quantity": 1,
            }
        ]
        # Replace old shipping item
        line_items += [{"id": user.active_subscription.shipping_si.id, "deleted": True}]

    #### Apply changes

    stripe.Subscription.modify(
        subscription_id,
        proration_behavior=proration_behaviour,
        items=line_items,
    )
