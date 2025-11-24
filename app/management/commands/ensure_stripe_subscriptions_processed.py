from django.core.management.base import BaseCommand
from app.models import User
from app.utils.shopify import create_shopify_order
import stripe


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the command without making changes',
        )
        parser.add_argument(
            '--ignore-all',
            action='store_true',
            help='Mark all unprocessed subscriptions as processed without creating Shopify orders',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        ignore_all = options['ignore_all']

        customers = stripe.Customer.list(limit=100)
    
        for customer in customers.auto_paging_iter():
            subscriptions = stripe.Subscription.list(customer=customer.id)
            for subscription in subscriptions.auto_paging_iter():
                # Skip non-active subscriptions
                if subscription.status != 'active':
                    print(f"Customer: {customer.email}")
                    print(f"  Subscription ID: {subscription.id}")
                    print(f"  Status: {subscription.status} (skipped - not active)\n")
                    if not dry_run:
                        stripe.Subscription.modify(subscription.id, metadata={"processed": "True"})
                        print(f"Customer {customer.email} subscription marked as processed\n")
                    continue
                print(f"Customer: {customer.email}")
                print(f"  Subscription ID: {subscription.id}")
                print(f"  Status: {subscription.status}")
                try:
                    print(f"Customer {customer.email} metadata: {subscription.metadata}")
                    if not subscription.metadata:
                        if ignore_all:
                            if not dry_run:
                                stripe.Subscription.modify(subscription.id, metadata={"processed": "True"})
                            print(f"Customer {customer.email} subscription marked as processed (ignore-all)\n")
                            continue

                        user = User.objects.filter(email=customer.email).first()
                        if user:
                            if user.primary_product:
                                if not dry_run:
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
                                print(f"Customer {customer.email} created shopify order {user.primary_product.name}")
                                
                            else:
                                print(f"Customer {customer.email} has no primary product")
                            if not dry_run:
                                stripe.Subscription.modify(subscription.id, metadata={"processed": "True"})
                            print(f"Customer {customer.email} subscription processed")
                        else:
                            print(f"Customer {customer.email} user not found\n")
                    else:
                        print(f"Customer {customer.email}: already processed.\n")
                    
                except Exception as e:
                    from sentry_sdk import capture_exception, capture_message
                    
                    print(f"User {customer.email} error: {e}")

                    # Log to Sentry
                    capture_exception(e)
                    capture_message(
                        f"[StripeCheckoutSuccess] Failed to complete processing for user {customer.email}"
                    )