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

    def legacy_data_to_stripe_address(user):
        return {
            "line1": user.address1,
            "line2": user.address2,
            "postal_code": user.postcode,
            "city": user.city,
            "state": user.state,
            "country": user.country,
        }

    @transaction.atomic
    def handle(self, *args, **options):
        batch_size = options.get("batch_size")
        legacy_users = (
            User.objects.annotate(stripe_id_length=Length("stripe_id"))
            .filter(stripe_id_length__gt=1, djstripe_customers=None)
            .all()[:batch_size]
        )
        print("Syncing legacy users", len(legacy_users))
        for user in legacy_users:
            if user.stripe_id is not None and len(user.stripe_id) > 0:
                try:
                    stripe_customer = None
                    try:
                        stripe_customer = stripe.Customer.retrieve(user.stripe_id)
                    except:
                        pass

                    if stripe_customer is None:
                        """
                        Create a new stripe customer if required
                        """
                        stripe_customer = stripe.Customer.search(
                            query=f"metadata['legacy_id']:'{user.old_id}'",
                        )
                        if stripe_customer is None:
                            stripe_customer = stripe.Customer.create(
                                name=user.get_full_name(),
                                email=user.email,
                                address=self.legacy_data_to_stripe_address(user),
                                shipping={
                                    "name": user.get_full_name(),
                                    "address": self.legacy_data_to_stripe_address(user),
                                },
                                metadata={
                                    "legacy_id": user.old_id,
                                    "djstripe_subscriber": user.id,
                                },
                            )
                    elif user.address1:
                        """
                        Else update shipping data if possible
                        """
                        stripe_customer = stripe.Customer.modify(
                            stripe_customer.id,
                            shipping={
                                "name": user.get_full_name(),
                                "address": self.legacy_data_to_stripe_address(user),
                            },
                            metadata={
                                "legacy_id": user.old_id,
                                "djstripe_subscriber": user.id,
                            },
                        )

                    (
                        local_customer,
                        is_new,
                    ) = djstripe.models.Customer._get_or_create_from_stripe_object(
                        stripe_customer
                    )
                    local_customer.subscriber = user
                    local_customer.save()
                    djstripe.models.Customer.sync_from_stripe_data(stripe_customer)
                    user.stripe_customer._sync_subscriptions()
                    print(
                        "Sync complete ✅: historical stripe customer",
                        user.id,
                        user.stripe_id,
                    )
                except Exception as e:
                    print(
                        "Sync failed ❌: historical stripe customer",
                        user.id,
                        user.stripe_id,
                    )
                    raise e
