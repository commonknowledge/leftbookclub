import djstripe
import stripe
from allauth.account.models import EmailAddress
from allauth.account.utils import user_display
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from sentry_sdk import capture_exception

from app.utils.stripe import (
    get_primary_product_for_djstripe_subscription,
    interval_string_for_plan,
    subscription_with_promocode,
)

from .stripe import LBCProduct, LBCSubscription


def custom_user_casual_name(user: AbstractUser) -> str:
    fn = user.first_name
    if fn is not None and len(fn):
        return fn
    return user.username


class User(AbstractUser):
    gdpr_email_consent = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Book club emails",
        help_text="Can we email you with news and updates from the Left Book Club?",
    )

    # Fields imported from the old app
    old_id = models.IntegerField(null=True, blank=True, unique=True)
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
        except Exception as e:
            capture_exception(e)
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

    valid_subscription_statuses = [
        djstripe.enums.SubscriptionStatus.active,
        djstripe.enums.SubscriptionStatus.trialing,
        djstripe.enums.SubscriptionStatus.past_due,
        djstripe.enums.SubscriptionStatus.unpaid,
    ]

    @property
    def active_subscription(self) -> LBCSubscription:
        try:
            sub = (
                LBCSubscription.objects.filter(
                    customer=self.stripe_customer,
                    # Was started + wasn't cancelled
                    status__in=self.valid_subscription_statuses,
                    # Is in period
                    current_period_end__gt=timezone.now(),
                    # Isn't a gift card
                    metadata__gift_mode__isnull=True,
                )
                .order_by("-created")
                .first()
            )
            return sub
        except:
            return None

    @property
    def old_subscription(self) -> LBCSubscription:
        try:
            sub = (
                self.stripe_customer.subscriptions.filter(
                    ended_at__isnull=False,
                    # Isn't a gift card
                    metadata__gift_mode__isnull=True,
                )
                .order_by("-ended_at")
                .first()
            )
            return sub
        except:
            return None

    @property
    def is_member(self):
        return self.active_subscription is not None

    @property
    def has_overdue_payment(self):
        return (
            self.is_member
            and self.active_subscription.status
            == djstripe.enums.SubscriptionStatus.past_due
        )

    @property
    def is_cancelling_member(self):
        return self.is_member and self.active_subscription.cancel_at is not None

    @property
    def is_expired_member(self):
        return not self.is_member and self.old_subscription is not None

    @property
    def has_never_subscribed(self):
        return (
            self.stripe_customer is None
            or self.stripe_customer.subscriptions.count() == 0
        )

    def subscription_status(self):
        if self.is_member:
            return self.active_subscription.status
        return None

    @property
    def primary_product(self) -> LBCProduct:
        try:
            if self.active_subscription is not None:
                product = get_primary_product_for_djstripe_subscription(
                    self.active_subscription.lbc
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
        if self.stripe_customer is not None:
            return (
                self.stripe_customer.subscriptions.filter(
                    metadata__gift_mode__isnull=False
                )
                .all()
                .order_by("-created")
            )
        return list()

    @property
    def gift_giver(self):
        try:
            user = self.active_subscription.gift_giver_subscription.customer.subscriber
            return user
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
            customer = customer._api_update(
                name=str(self), metadata={"gdpr_email_consent": self.gdpr_email_consent}
            )
            self.refresh_stripe_data()
        except:
            pass
        return customer, True

    @property
    def primary_email(self):
        return self.email

        # primary = EmailAddress.objects.get_primary(self)
        # if primary is not None:
        #     return primary.email
        # allauth_emails = EmailAddress.objects.filter(user=self).order_by(
        #     "primary", "verified"
        # )
        # if len(allauth_emails) > 0:
        #     return allauth_emails[0].email
        # return self.email

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
        return self.shipping_address.get("line1", None)

    def shipping_line_2(self):
        return self.shipping_address.get("line2", None)

    def shipping_city(self):
        return self.shipping_address.get("city", None)

    def shipping_state(self):
        return self.shipping_address.get("state", None)

    def shipping_country(self):
        return self.shipping_address.get("country", None)

    def shipping_postcode(self):
        return self.shipping_address.get("postal_code", None)

    def cleanup_membership_subscriptions(self, keep=[]):
        for sub in self.stripe_customer.subscriptions.all():
            if sub.metadata.get("gift_mode", None) is None and not sub.id in keep:
                try:
                    stripe.Subscription.delete(sub.id, prorate=True)
                except:
                    pass
        self.refresh_stripe_data()

    @property
    def subscription_billing_interval(self):
        try:
            if self.active_subscription is not None:
                si = self.active_subscription.items.first()
                return interval_string_for_plan(si.plan)
        except:
            return None

    @property
    def subscription_price(self):
        try:
            if self.active_subscription is not None:
                si = self.active_subscription.items.first()
                return si.plan.human_readable_price
        except:
            return None

    def get_analytics_data(self):
        user_data = {
            "is_authenticated": True,
            "set": {
                "django_id": self.id
                if settings.STRIPE_LIVE_MODE
                else f"{self.id}-DEBUGGING",
                "email": self.email
                if settings.STRIPE_LIVE_MODE
                else f"DEBUGGING--{self.email}",
                "name": self.get_full_name(),
                "stripe_customer_id": self.stripe_customer.id
                if self.stripe_customer is not None
                else None,
                "staff": self.is_staff,
            },
            "register": {},
        }

        if self.primary_product is not None:
            subscription_data = {
                "subscription_billing_interval": self.subscription_billing_interval,
                "subscription_price": str(self.subscription_price),
                "primary_stripe_product_name": self.primary_product.name,
                "primary_stripe_product_id": self.primary_product.id,
            }
            user_data["register"].update(subscription_data)
            user_data["set"].update(
                {
                    **subscription_data,
                    **{
                        "shipping_city": self.shipping_city(),
                        "shipping_country": self.shipping_country(),
                    },
                }
            )

        if self.gifts_bought is not None and len(self.gifts_bought):
            data = {"gifts_bought": len(self.gifts_bought)}
            user_data["register"].update(data)
            user_data["set"].update(data)

        if self.gift_giver is not None:
            data = {"gift_recipient": True}
            user_data["register"].update(data)
            user_data["set"].update(data)

        return user_data
