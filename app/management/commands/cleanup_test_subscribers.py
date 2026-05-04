import djstripe.models
import stripe
from django.core.management.base import BaseCommand

# Test accounts that show up as active members in the export
# but should not — Stripe says one is cancelled and the other has no sub.
TEST_EMAILS = [
    "joaquim+gift@commonknowledge.coop",  # Darius Chira
    "joaquim@commonknowledge.coop",       # Esha Grewal
]


class Command(BaseCommand):
    help = (
        "Clean up stale djstripe Subscription rows for known test accounts so "
        "they stop appearing in the active members export. Syncs from Stripe "
        "if the sub still exists there; deletes the local row if it doesn't."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        for email in TEST_EMAILS:
            self.cleanup(email, dry_run=options["dry_run"])

    def cleanup(self, email, dry_run=False):
        customers = djstripe.models.Customer.objects.filter(email=email)
        if not customers.exists():
            self.stdout.write(f"— {email}: no djstripe Customer found")
            return

        for customer in customers:
            subs = djstripe.models.Subscription.objects.filter(customer=customer)
            self.stdout.write(
                f"→ {email} (customer={customer.id}): {subs.count()} local sub(s)"
            )

            for sub in subs:
                try:
                    stripe_sub = stripe.Subscription.retrieve(sub.id)
                except stripe.error.InvalidRequestError as e:
                    if "No such subscription" in str(e):
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ✂  {sub.id}: not in Stripe — deleting local row"
                            )
                        )
                        if not dry_run:
                            sub.delete()
                        continue
                    raise

                self.stdout.write(
                    f"  ↻ {sub.id}: Stripe status={stripe_sub.status}, local status={sub.status} — syncing"
                )
                if not dry_run:
                    djstripe.models.Subscription.sync_from_stripe_data(stripe_sub)
