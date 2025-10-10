from typing import Optional

import shopify
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import BookPage, LBCSubscription
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
            "--proration_behaviour",
            dest="proration_behaviour",
            default="none",
            help="Proration behaviour",
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
        execute, args, kwargs = process(**options)
        execute(*args, **kwargs)


import traceback

import djstripe.enums
import djstripe.models
import stripe


def run(job):
    context = {}
    try:
        execute, args, kwargs = process(**job.workspace)
        context = {
            "args": args,
            "kwargs": kwargs,
        }
        execute(*args, **kwargs)
    except Exception as e:
        error = traceback.format_exc()
        job.workspace = {
            **job.workspace,
            "error": str(e),
            "error_trace": error,
            "context": context,
        }
        job.save()
        raise e


def process(
    subscription_id: str,
    proration_behaviour: str = "none",
    add_or_update_shipping=False,
    optional_custom_shipping_fee=None,
    update_membership_fee=False,
    optional_custom_membership_fee=None,
    **kwargs,
):
    #### Refresh data
    st_sub = stripe.Subscription.retrieve(subscription_id)
    djstripe.models.Subscription.sync_from_stripe_data(st_sub)
    dj_sub = LBCSubscription.objects.get(id=subscription_id)

    if dj_sub is None:
        raise ValueError("Sub not found in Django database")

    if dj_sub.membership_plan_price is None or dj_sub.membership_si is None:
        raise ValueError("Sub is not a membership")

    if dj_sub.status == djstripe.enums.SubscriptionStatus.canceled:
        raise ValueError("Sub is canceled: cannot be charged")

    if dj_sub.is_gift_receiver:
        raise ValueError("Sub is a gift recipient: cannot be charged")

    #### Create line items

    line_items = []

    if update_membership_fee:
        # Create new membership item
        line_items += [
            {
                "price_data": dj_sub.membership_plan_price.to_price_data(
                    product=dj_sub.membership_si.plan.product,
                    amount=optional_custom_membership_fee,
                ),
                "quantity": 1,
            }
        ]
        # Replace old membership item
        if dj_sub.membership_si is not None:
            line_items += [{"id": dj_sub.membership_si.id, "deleted": True}]

    if add_or_update_shipping:
        # Create new shipping item
        line_items += [
            {
                "price_data": dj_sub.membership_plan_price.to_shipping_price_data(
                    zone=dj_sub.shipping_zone,
                    amount=optional_custom_shipping_fee,
                ),
                "quantity": 1,
                "tax_rates": [],
            }
        ]
        # Replace old shipping item
        if dj_sub.shipping_si is not None:
            line_items += [{"id": dj_sub.shipping_si.id, "deleted": True}]

    #### Apply changes

    args = [subscription_id]

    kwargs = dict(
        proration_behavior=proration_behaviour,
        items=line_items,
    )

    def execute(*args, **kwargs):
        stripe.Subscription.modify(*args, **kwargs)

    return [execute, args, kwargs]
