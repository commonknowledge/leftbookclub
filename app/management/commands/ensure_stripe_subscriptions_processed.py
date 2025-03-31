from django.core.management.base import BaseCommand
from app.models import User
from app.utils.shopify import create_shopify_order
import stripe


class Command(BaseCommand):
    def handle(self, *args, **options):
        users = User.objects.order_by("email")
        for user in users:
            print(f"Checking user {user.email}")
            if not user.stripe_customer:
                print(f"User {user.email}: not a stripe customer, skipping\n")
                continue
            sub = user.stripe_customer.subscriptions.first()
            if not sub:
                print(f"User {user.email}: no subscription, skipping\n")
                continue
            if sub.metadata.get("processed"):
                print(f"User {user.email}: subscription already processed, skipping\n")
                continue

            print(f"User {user.email}: processing subscription...")
            
            if not user.primary_product:
                print(f"User {user.email}: has no primary product, skipping\n")
                continue

            create_shopify_order(
                user,
                line_items=[
                    {
                        "title": f"Membership Subscription Purchase — {user.primary_product.name}",
                        "quantity": 1,
                        "price": 0,
                    }
                ],
                tags=["Membership Subscription Purchase", "Manual Sync"],
            )
            stripe.Subscription.modify(sub.id, metadata={"processed": "True"})

            print(f"User {user.email}: processed.\n")
