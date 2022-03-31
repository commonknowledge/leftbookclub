import djstripe
from allauth.account.utils import user_display
from django.contrib.auth.models import AbstractUser

from .stripe import LBCProduct


def custom_user_display(user: AbstractUser) -> str:
    fn = user.get_full_name()
    if fn is not None and len(fn):
        return fn
    return user.username


def custom_user_casual_name(user: AbstractUser) -> str:
    fn = user.first_name
    if fn is not None and len(fn):
        return fn
    return user.username


class User(AbstractUser):
    @property
    def display_name(self):
        return user_display(self)

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
            sub = self.stripe_customer.subscriptions.first()
            return sub
        except:
            return None

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

    def get_or_create_customer(self):
        if self.stripe_customer is not None:
            return self.stripe_customer, False

        customer = djstripe.models.Customer.create(subscriber=self)
        try:
            customer = customer._api_update(name=custom_user_display(self))
            djstripe.models.Customer._sync_from_stripe_data(customer)
        except:
            pass
        return customer, True
