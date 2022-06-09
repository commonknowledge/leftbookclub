import djstripe.models
import stripe
from django.conf import settings
from django.core.management.base import BaseCommand
from djstripe.enums import SubscriptionStatus

from app.management.commands.migrate_old_stripe_subscriptions import (
    get_replacement_plan_for_old_plan,
)
from app.models.django import User
from app.models.legacy import LegacyGifts
from app.models.stripe import LBCProduct, LBCSubscription
from app.utils.stripe import get_gift_card_coupon, recreate_one_off_stripe_price

invalid_statuses = [
    SubscriptionStatus.canceled.lower(),
    SubscriptionStatus.incomplete_expired.lower(),
]


class Command(BaseCommand):
    help = "Create BookPage for each Shopify product"

    def add_arguments(self, parser):
        parser.add_argument(
            "-b", "--batch", dest="batch_size", type=int, default=100000
        )

        parser.add_argument("-p", "--product", dest="product", type=str, default=None)

        parser.add_argument(
            "-s", "--subscription", dest="subscription", type=str, default=None
        )

        parser.add_argument(
            "-es", "--excluded_subs", dest="excluded_subs", nargs="+", default=[]
        )

    def handle(self, *args, **options):
        subs_with_discounts = (
            LBCSubscription.objects.filter(discount__coupon__name__isnull=False)
            .exclude(status__in=invalid_statuses)
            .all()
        )
        for sub in subs_with_discounts:
            old_coupon_name = sub.discount.get("coupon", {}).get("name", "")
            old_coupon_id = sub.discount.get("coupon", {}).get("id", "")

            if old_coupon_name is not None and "Gift Card:" in old_coupon_name:
                # For gift recipients with no named price
                # (as this wasn't managed in the migrate_old_stripe_subscriptions script)
                old_si = sub.items.first()
                if old_si.plan.nickname is None:
                    # use their gift_giver_subscription primary product as a guide to what product to move them to
                    gift_giver_subscription = LBCSubscription.objects.get(
                        id=sub.metadata.get("gift_giver_subscription")
                    )
                    stripe_price = stripe.Price.retrieve(
                        gift_giver_subscription.items.first().plan.id
                    )
                    new_plan = stripe.Price.create(
                        recreate_one_off_stripe_price(stripe_price)
                    )

                    # add the new si to the subscription
                    stripe.SubscriptionItem.create(
                        subscription=sub.id,
                        price=new_plan.id,
                        quantity=1,
                    )

                    # delete the old si
                    stripe.SubscriptionItem.delete(old_si.id)

                    # update
                    subscription = stripe.Subscription.retrieve(sub.id)
                    sub = djstripe.models.Subscription.sync_from_stripe_data(
                        subscription
                    )

                # Migrate all old gift cards to their matching product gift card
                # As this wasn't managed in the migrate_old_stripe_subscriptions script
                coupon = get_gift_card_coupon(sub.primary_product)
                if coupon.id == old_coupon_id:
                    print(
                        f"🔵 No coupon upgrade required {sub.primary_product.name} [{sub.id}] -- {old_coupon_name} [{old_coupon_id}]"
                    )
                else:
                    new_sub = stripe.Subscription.modify(sub.id, coupon=coupon.id)
                    djstripe.models.Subscription.sync_from_stripe_data(new_sub)
                    print(
                        f"🟢 Updated subscription to use new coupon: {sub.primary_product.name} [{sub.id}] -- {old_coupon_name} [{old_coupon_id}] -> {coupon.name} [{coupon.id}]"
                    )

                # Ensure there's no non-£0 invoice coming up
                invoice = stripe.Invoice.upcoming(
                    customer=sub.customer.id,
                )
                if invoice.amount_remaining > 0:
                    stripe.Customer.create_balance_transaction(
                        sub.customer.id,
                        amount=invoice.amount_remaining,
                        currency=invoice.currency,
                    )
