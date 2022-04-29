import djstripe.models
import stripe
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.functions import Length

from app.models.django import User


class Command(BaseCommand):
    help = "Create BookPage for each Shopify product"

    def add_arguments(self, parser):
        parser.add_argument(
            "-b", "--batch", dest="batch_size", type=int, default=100000
        )

    @transaction.atomic
    def handle(self, *args, **options):
        batch_size = options.get("batch_size")
        legacy_users = (
            User.objects.annotate(stripe_id_length=Length("stripe_id"))
            .filter(stripe_id_length__gt=1, djstripe_customers=None)
            .all()[:batch_size]
        )
        print("Syncing legacy users", len(legacy_users))
        for u in legacy_users:
            if u.stripe_id is not None and len(u.stripe_id) > 0:
                try:
                    print(
                        "Sync starting: historical stripe customer",
                        u.id,
                        u.stripe_id,
                    )
                    stripe_customer = stripe.Customer.retrieve(u.stripe_id)

                    if stripe_customer is None:
                        print("No such stripe customer found", u.stripe_id)
                        # u.stripe_id = None
                        # u.save()
                        continue

                    if u.address1:
                        stripe.Customer.modify(
                            self.stripe_customer.id,
                            shipping={
                                "name": self.get_full_name(),
                                "address": {
                                    "line1": self.address1,
                                    "line2": self.address2,
                                    "postal_code": self.postcode,
                                    "city": self.city,
                                    "state": self.state,
                                    "country": self.country,
                                },
                            },
                        )
                        print(
                            "Updated shipping",
                            u.id,
                            u.stripe_id,
                        )

                    (
                        local_customer,
                        is_new,
                    ) = djstripe.models.Customer._get_or_create_from_stripe_object(
                        stripe_customer
                    )
                    local_customer.subscriber = u.request.user
                    local_customer.save()
                    djstripe.models.Customer.sync_from_stripe_data(stripe_customer)
                    u.stripe_customer._sync_subscriptions()
                    print(
                        "Sync complete ✅: historical stripe customer",
                        u.id,
                        u.stripe_id,
                    )
                except Exception as e:
                    print(
                        "Sync failed ❌: historical stripe customer",
                        u.id,
                        u.stripe_id,
                    )
                    raise e
