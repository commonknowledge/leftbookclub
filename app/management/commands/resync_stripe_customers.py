import djstripe.models
import stripe
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Re-sync all djstripe Customer records from the Stripe API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            dest="email",
            type=str,
            default=None,
            help="Only sync the customer with this email address",
        )

    def handle(self, *args, **options):
        email = options.get("email")

        qs = djstripe.models.Customer.objects.filter(deleted=False)
        if email:
            qs = qs.filter(email=email)

        customers = list(qs.values_list("id", flat=True))
        total = len(customers)
        self.stdout.write(f"Syncing {total} customer(s) from Stripe...")

        ok = 0
        errors = 0
        for stripe_id in customers:
            try:
                stripe_customer = stripe.Customer.retrieve(stripe_id)
                self.stdout.write(f"  {stripe_id} — from Stripe:")
                self.stdout.write(f"    address:  {stripe_customer.get('address')}")
                self.stdout.write(f"    shipping: {stripe_customer.get('shipping')}")
                djstripe.models.Customer.sync_from_stripe_data(stripe_customer)
                ok += 1
                self.stdout.write(f"  OK: {stripe_id}")
            except Exception as e:
                errors += 1
                self.stderr.write(f"  ERROR: {stripe_id} — {e}")

        self.stdout.write(f"\nDone. {ok} synced, {errors} errors.")
