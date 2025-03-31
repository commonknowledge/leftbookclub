from django.core.management.base import BaseCommand
from app.models import User
from app.utils.shopify import create_shopify_order
import stripe


class Command(BaseCommand):
    def handle(self, *args, **options):
        customers = stripe.Customer.list(limit=100)
    
        for customer in customers.auto_paging_iter():
            subscriptions = stripe.Subscription.list(customer=customer.id)
            for subscription in subscriptions.auto_paging_iter():
                print(f"Customer: {customer.email}")
                print(f"  Subscription ID: {subscription.id}")
                print(f"  Status: {subscription.status}")
                try:
                    print(f"Customer {customer.email} metadata: {subscription.metadata}")
                    if not subscription.metadata:
                        user = User.objects.filter(email=customer.email).first()
                        if user:
                            if user.primary_product:
                                
                                create_shopify_order(
                                    customer,
                                    line_items=[
                                        {
                                            "title": f"Membership Subscription Purchase — {user.primary_product.name}",
                                            "quantity": 1,
                                            "price": 0,
                                        }
                                    ],
                                    tags=["Membership Subscription Purchase", "Manual Sync"],
                                )
                                print(print(f"Customer {customer.email} created shopify order {user.primary_product.name}"))
                               
                                
                            else:
                                print(f"Customer {customer.email} has no primary product")
                            
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

