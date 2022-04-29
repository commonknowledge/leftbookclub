import djstripe
import stripe
from allauth.account.models import EmailAddress
from allauth.account.utils import user_display
from django.contrib.auth.models import AbstractUser
from django.db import models

from app.utils.stripe import (
    get_primary_product_for_djstripe_subscription,
    subscription_with_promocode,
)

from .stripe import LBCProduct


def custom_user_casual_name(user: AbstractUser) -> str:
    fn = user.first_name
    if fn is not None and len(fn):
        return fn
    return user.username


class User(AbstractUser):
    # Fields imported from the old app
    old_id = models.IntegerField(null=True, blank=True)
    tel = models.CharField(max_length=191, null=True, blank=True)
    address1 = models.CharField(max_length=191, null=True, blank=True)
    address2 = models.CharField(max_length=191, null=True, blank=True)
    city = models.CharField(max_length=191, null=True, blank=True)
    state = models.CharField(max_length=191, null=True, blank=True)
    country = models.CharField(max_length=191, null=True, blank=True)
    postcode = models.CharField(max_length=10, null=True, blank=True)
    gender = models.CharField(max_length=100, null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    occupation = models.CharField(max_length=191, null=True, blank=True)
    stripe_id = models.CharField(max_length=191, null=True, blank=True)

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
            elif self.stripe_id is not None and len(self.stripe_id) > 0:
                try:
                    print(
                        "Sync starting: historical stripe customer",
                        self.id,
                        self.stripe_id,
                    )
                    stripe_customer = stripe.Customer.retrieve(self.stripe_id)
                    (
                        local_customer,
                        is_new,
                    ) = djstripe.models.Customer._get_or_create_from_stripe_object(
                        stripe_customer
                    )
                    local_customer.subscriber = self.request.user
                    local_customer.save()
                    djstripe.models.Customer.sync_from_stripe_data(stripe_customer)
                    self.stripe_customer._sync_subscriptions()
                    print(
                        "Sync complete ✅: historical stripe customer",
                        self.id,
                        self.stripe_id,
                    )
                except:
                    print(
                        "Sync failed ❌: historical stripe customer",
                        self.id,
                        self.stripe_id,
                    )
        except:
            pass

    @property
    def stripe_customer(self) -> djstripe.models.Customer:
        try:
            customer = self.djstripe_customers.first()
            return customer
        except:
            return None

    def stripe_customer_id(self) -> str:
        customer = self.stripe_customer
        if customer:
            return customer.id
        return None

    @property
    def active_subscription(self) -> djstripe.models.Subscription:
        try:
            sub = self.stripe_customer.active_subscriptions.filter(
                metadata__gift_mode__isnull=True
            ).first()
            return sub
        except:
            return None

    @property
    def is_member(self):
        return self.active_subscription is not None

    def subscription_status(self):
        if self.is_member:
            return self.active_subscription.status
        return None

    @property
    def subscribed_product(self) -> LBCProduct:
        try:
            if self.active_subscription is not None:
                product = get_primary_product_for_djstripe_subscription(
                    self.active_subscription
                )
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

    @property
    def gifts_bought(self):
        return (
            self.stripe_customer.subscriptions.filter(metadata__gift_mode__isnull=False)
            .all()
            .order_by("-created")
        )

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

    @property
    def shipping_address(self):
        try:
            shipping = self.stripe_customer.shipping.get("address", {})
            return shipping
        except:
            return {}

    def shipping_name(self):
        try:
            name = None
            if self.get_full_name() is not None:
                name = self.get_full_name()
            if name is None or len(name) == 0:
                try:
                    name = self.stripe_customer.shipping.get("name", None)
                except:
                    pass
            if name is None or len(name) == 0:
                try:
                    name = self.stripe_customer.name
                except:
                    pass
            if name is None or len(name) == 0:
                name = self.username
            return name
        except:
            return ""

    def shipping_line_1(self):
        return self.shipping_address.get("line1", "")

    def shipping_line_2(self):
        return self.shipping_address.get("line2", None)

    def shipping_line_2(self):
        return self.shipping_address.get("line2", None)

    def shipping_city(self):
        return self.shipping_address.get("city", None)

    def shipping_country(self):
        return self.shipping_address.get("country", None)

    def shipping_zip(self):
        return self.shipping_address.get("zip", None)

    def cleanup_membership_subscriptions(self, keep=[]):
        for sub in self.stripe_customer.subscriptions.all():
            if sub.metadata.get("gift_mode", None) is None and not sub.id in keep:
                try:
                    stripe.Subscription.delete(sub.id, prorate=True)
                except:
                    pass
        self.refresh_stripe_data()
