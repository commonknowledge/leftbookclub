import djstripe.models
import stripe
from django.core.management.base import BaseCommand

from app.models.stripe import ShippingZone
from app.utils.stripe import (
    DONATION_PRODUCT_NAME,
    create_one_off_shipping_price_data_for_price,
    get_gift_card_coupon,
    recreate_one_off_stripe_price,
)

# Cancelled gift-recipient subscription IDs to rebuild.
# The 100%-off gift coupon stopped covering postage after a price rise,
# Stripe charged £3.50, the recipient's card failed, and the sub was cancelled.
RECIPIENT_SUB_IDS = [
    "sub_1RxyozKYdS0VccAE9OeDezF2",  # Temple Daniel
    "sub_1RpnhoKYdS0VccAElU8y8Z3v",  # Rosa Tully
]


class Command(BaseCommand):
    help = "Reactivate two specific cancelled gift-recipient subscriptions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be done without creating subs",
        )

    def handle(self, *args, **options):
        for recipient_sub_id in RECIPIENT_SUB_IDS:
            try:
                self.reactivate(recipient_sub_id, dry_run=options["dry_run"])
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {recipient_sub_id}: {e}"))

    def reactivate(self, recipient_sub_id, dry_run=False):
        old_recipient_sub = stripe.Subscription.retrieve(
            recipient_sub_id,
            expand=["items.data.price.product"],
        )

        giver_sub_id = old_recipient_sub.metadata.get("gift_giver_subscription")
        if not giver_sub_id:
            raise ValueError("no gift_giver_subscription on recipient metadata")

        giver_sub = stripe.Subscription.retrieve(giver_sub_id)
        customer_id = old_recipient_sub.customer

        items = []
        membership_product_id = None
        for si in old_recipient_sub["items"]["data"]:
            price = si.price
            product = price.product
            product_name = (
                product["name"] if isinstance(product, dict) else getattr(product, "name", None)
            )

            if price.metadata.get("shipping_zone"):
                zone = ShippingZone.get_for_code(
                    code=price.metadata.get("shipping_zone", "ROW")
                )
                items.append(
                    {
                        "price_data": create_one_off_shipping_price_data_for_price(
                            price, zone
                        ),
                        "quantity": si.quantity,
                    }
                )
            elif product_name == DONATION_PRODUCT_NAME:
                continue
            else:
                items.append(
                    {
                        "price_data": recreate_one_off_stripe_price(
                            price.id, metadata={"primary": True}
                        ),
                        "quantity": si.quantity,
                    }
                )
                membership_product_id = (
                    product["id"] if isinstance(product, dict) else product.id
                )

        if membership_product_id is None:
            raise ValueError("no membership item found on canceled sub")

        coupon = get_gift_card_coupon(membership_product_id)
        promo_code_id = giver_sub.metadata.get("promo_code")

        self.stdout.write(
            f"→ {recipient_sub_id}: giver={giver_sub_id}, customer={customer_id}, "
            f"membership_product={membership_product_id}, coupon={coupon.id}, items={len(items)}"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("  (dry-run, skipping create)"))
            return

        new_sub = stripe.Subscription.create(
            customer=customer_id,
            items=items,
            coupon=coupon.id,
            payment_behavior="allow_incomplete",
            off_session=True,
            metadata={
                "gift_giver_subscription": giver_sub.id,
                "promo_code": promo_code_id,
            },
        )
        djstripe.models.Subscription.sync_from_stripe_data(new_sub)

        stripe.Subscription.modify(
            giver_sub.id,
            metadata={
                **dict(giver_sub.metadata),
                "gift_recipient_subscription": new_sub.id,
            },
        )

        # Refresh recipient's djstripe customer so the user sees the new sub
        dj_customer = djstripe.models.Customer.objects.filter(id=customer_id).first()
        if dj_customer is not None and dj_customer.subscriber is not None:
            dj_customer.subscriber.refresh_stripe_data()

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {recipient_sub_id}: created replacement recipient sub {new_sub.id}"
            )
        )
