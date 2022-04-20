import djstripe
import stripe
from allauth.account.models import EmailAddress
from allauth.account.utils import user_display
from django.contrib.auth.models import AbstractUser

from .stripe import LBCProduct


def custom_user_casual_name(user: AbstractUser) -> str:
    fn = user.first_name
    if fn is not None and len(fn):
        return fn
    return user.username


class User(AbstractUser):
    @property
    def display_name(self):
        return user_display(self)

    def refresh_stripe_data(self):
        try:
            if self.stripe_customer is not None:
                # Refetch customer data
                customer = stripe.Customer.retrieve(self.stripe_customer.id)
                djstripe.models.Customer.sync_from_stripe_data(customer)
                # Update subscriptions
                self.stripe_customer._sync_subscriptions()
        except:
            pass

    @property
    def stripe_customer(self) -> djstripe.models.Customer:
        try:
            customer = self.djstripe_customers.first()
            return customer
        except:
            return None

    @property
    def active_subscription(self) -> djstripe.models.Subscription:
        try:
            sub = self.stripe_customer.active_subscriptions.first()
            return sub
        except:
            return None

    @property
    def is_member(self):
        return self.active_subscription is not None

    @property
    def subscribed_product(self) -> LBCProduct:
        try:
            product = self.active_subscription.plan.product
            return product
        except:
            return None

    @property
    def subscribed_price(self):
        try:
            product = self.active_subscription.plan.subscription_items.first().price
            return product
        except:
            return None

    def __str__(self) -> str:
        fn = self.get_full_name()
        if fn is not None and len(fn):
            return fn
        return self.username

    def get_or_create_customer(self):
        if self.stripe_customer is not None:
            return self.stripe_customer, False

        customer = djstripe.models.Customer.create(subscriber=self)
        try:
            customer = customer._api_update(name=str(self))
            self.refresh_stripe_data()
        except:
            pass
        return customer, True

    @property
    def primary_email(self):
        primary = EmailAddress.objects.get_primary(self)
        if primary is not None:
            return primary.email
        allauth_emails = EmailAddress.objects.filter(user=self).order_by(
            "primary", "verified"
        )
        if len(allauth_emails) > 0:
            return allauth_emails[0].email
        return self.email
