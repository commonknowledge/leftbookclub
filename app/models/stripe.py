from typing import Any, Dict, List, Optional, Tuple

from dataclasses import dataclass

import djstripe.models
import stripe
from django import forms
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Length
from django.forms import RadioSelect
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_countries import countries as django_countries
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from djmoney.models.fields import Money, MoneyField
from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet

from app.utils import flatten_list
from app.utils.django import add_proxy_method
from app.utils.stripe import (
    DONATION_PRODUCT_NAME,
    SHIPPING_PRODUCT_NAME,
    get_donation_product,
    get_primary_product_for_djstripe_subscription,
)


class LBCCustomer(djstripe.models.Customer):
    class Meta:
        proxy = True


add_proxy_method(djstripe.models.Customer, LBCCustomer, "lbc")


class LBCSubscription(djstripe.models.Subscription):
    class Meta:
        proxy = True

    @cached_property
    def primary_product(self):
        return get_primary_product_for_djstripe_subscription(self)

    def primary_product_name(self):
        if self.primary_product:
            return self.primary_product.name

    def primary_product_id(self):
        if self.primary_product:
            return self.primary_product.id

    def customer_id(self):
        return self.customer.id

    GIFT_GIVER_SUB_METADATA_KEY = "gift_giver_subscription"

    @cached_property
    def gift_giver_subscription(self):
        """
        If this subscription was created as a result of a neighbouring gift subscription
        """
        related_subscription_id = self.metadata.get(
            self.GIFT_GIVER_SUB_METADATA_KEY, None
        )
        if related_subscription_id:
            return LBCSubscription.objects.filter(id=related_subscription_id).first()

    @cached_property
    def gift_recipient_subscription(self):
        """
        If this subscription was created as a result of a neighbouring gift subscription
        """
        related_subscription_id = self.metadata.get("gift_recipient_subscription", None)
        if related_subscription_id:
            return LBCSubscription.objects.filter(id=related_subscription_id).first()

    @property
    def is_gift_giver(self):
        self.metadata.get("gift_mode", None) is not None

    @property
    def is_gift_receiver(self):
        self.metadata.get(self.GIFT_GIVER_SUB_METADATA_KEY, None) is not None

    def recipient_name(self):
        try:
            user = self.customer.subscriber
            return user.shipping_name()
        except:
            return None

    def recipient_email(self):
        try:
            return self.customer.email
        except:
            return None

    def is_active_member(self):
        try:
            user = self.customer.subscriber
            return user.is_member
        except:
            return None

    def upsert_regular_donation(self, amount: float, metadata: Dict[str, Any] = dict()):
        if amount < 0:
            raise ValueError("Donation amount must be 0 or greater.")

        # Modify the stripe subscription with a donation product and the amount arg
        items = []

        # Get the existing donation SI if it exists, and delete it
        donation_si = self._named_subscription_items().donation_si
        if donation_si is not None:
            items.append({"id": donation_si.id, "deleted": True})

        if amount > 0:
            # Create a new donation SI with the amount arg
            plan = self.items.first().plan
            items.append(
                {
                    "price_data": {
                        "unit_amount_decimal": int(amount * 100),
                        "product": get_donation_product().id,
                        "metadata": {**metadata},
                        # Mirror details from another SI
                        "currency": plan.currency,
                        "recurring": {
                            "interval": plan.interval,
                            "interval_count": plan.interval_count,
                        },
                    },
                    "quantity": 1,
                }
            )

        subscription = stripe.Subscription.modify(
            self.id, proration_behavior="none", items=items
        )

        sub = djstripe.models.Subscription.sync_from_stripe_data(subscription)
        return sub.lbc

    @property
    def customer_shipping_address(self):
        try:
            shipping = self.customer.shipping
            address = shipping.get("address", {})
            return address
        except:
            return {}

    def shipping_line_1(self):
        return self.customer_shipping_address.get("line1", None)

    def shipping_line_2(self):
        return self.customer_shipping_address.get("line2", None)

    def shipping_city(self):
        return self.customer_shipping_address.get("city", None)

    def shipping_state(self):
        return self.customer_shipping_address.get("state", None)

    def shipping_country(self):
        return self.customer_shipping_address.get("country", None)

    def shipping_postcode(self):
        return self.customer_shipping_address.get("postal_code", None)

    @dataclass
    class NamedSubscriptionItems:
        membership_si: Optional[djstripe.models.SubscriptionItem] = None
        shipping_si: Optional[djstripe.models.SubscriptionItem] = None
        donation_si: Optional[djstripe.models.SubscriptionItem] = None

    def _named_subscription_items(self):
        sis = self.items.select_related("plan__product").all()

        details = self.NamedSubscriptionItems()

        for si in sis:
            if si.plan.product.name == SHIPPING_PRODUCT_NAME:
                details.shipping_si = si
            elif si.plan.product.name == DONATION_PRODUCT_NAME:
                details.donation_si = si
            else:
                details.membership_si = si

        return details

    @cached_property
    def named_subscription_items(self):
        return self._named_subscription_items()

    @property
    def membership_si(self):
        return self.named_subscription_items.membership_si

    @property
    def shipping_si(self):
        return self.named_subscription_items.shipping_si

    @property
    def donation_si(self):
        return self.named_subscription_items.donation_si

    @property
    def includes_donation(self):
        return self.donation_si is not None

    @property
    def no_shipping_line(self):
        return self.shipping_si is None

    @property
    def non_zero_shipping(self):
        return self.shipping_si is not None and self.shipping_si.plan.amount > 0

    @cached_property
    def membership_plan_price(self):
        from app.models import MembershipPlanPrice

        if self.membership_si is None:
            return None
        return MembershipPlanPrice.from_si(self.membership_si)

    @cached_property
    def shipping_zone(self):
        if self.shipping_si is not None:
            code = self.shipping_si.metadata.get("shipping_zone", None)
            if code is not None:
                result = ShippingZone.get_for_code(code)
                if result is not None:
                    return result
        shipping_country = self.customer.subscriber.shipping_country()
        if shipping_country is not None:
            return ShippingZone.get_for_country(shipping_country)

    @cached_property
    def has_legacy_membership_price(self):
        try:
            result = (
                self.membership_si.plan.amount < self.membership_plan_price.price.amount
            )
            return result
        except:
            return False

    @cached_property
    def should_upgrade(self):
        try:
            return self.has_legacy_membership_price or self.shipping_si is None
        except:
            return False

    @cached_property
    def next_fee(self):
        upcoming_invoice = stripe.Invoice.upcoming(
            customer=self.customer.id,
            subscription=self.id,
        )
        discount = 0
        for d in upcoming_invoice.total_discount_amounts:
            discount += d.amount

        return (upcoming_invoice.total - discount) / 100

    @property
    def price_string(self):
        if self.membership_plan_price is not None:
            return f"£{(self.next_fee):.2f}{self.membership_plan_price.humanised_interval()}"
        else:
            return f"£{(self.next_fee):.2f}"

    @property
    def next_billing_date(self):
        return self.current_period_end


add_proxy_method(djstripe.models.Subscription, LBCSubscription, "lbc")


@register_snippet
class LBCProduct(djstripe.models.Product):
    class Meta:
        proxy = True

    @classmethod
    def get_active_plans(self):
        plans = self.objects.filter(metadata__pickable="1", active=True, type="service")
        return list(
            sorted(plans, key=lambda p: p.basic_price.unit_amount, reverse=True)
        )

    @property
    def has_tiered_pricing(self):
        return self.prices.filter(nickname__isnull=False, active=True).exists()

    @property
    def basic_price(self):
        try:
            price = self.prices.get(nickname="basic", active=True)
            return price
        except:
            return (
                self.prices.filter(active=True)
                .exclude(nickname__icontains="archived")
                .order_by("unit_amount")
                .first()
            )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        from app.models import MembershipPlanPrice

        price = MembershipPlanPrice.objects.filter(products=self).first()
        s = getattr(self, self.autocomplete_search_field)
        if price:
            return f"{s} (applies to price: {price})"
        return s

    def get_prices_for_country(self, iso_a2: str, **kwargs):
        zone = ShippingZone.get_for_country(iso_a2)

        return djstripe.models.Price.objects.filter(
            product=self.id, active=True, metadata__shipping=zone.code, **kwargs
        ).order_by("unit_amount")

    @property
    def book_types(self):
        book_types = self.metadata.get("book_types", None)
        if book_types is not None:
            book_types = book_types.split(",")
            return book_types
        return list()

    @property
    def current_book(self):
        from app.models.wagtail import BookPage

        if self.book_types is not None and len(self.book_types) > 0:
            return (
                BookPage.objects.filter(type__in=self.book_types)
                .order_by("-published_date")
                .first()
            )
        return BookPage.objects.order_by("-published_date").first()


add_proxy_method(djstripe.models.Product, LBCProduct, "lbc")


alphanumeric = RegexValidator(
    r"^[0-9a-zA-Z]*$", "Only alphanumeric characters are allowed."
)


@register_snippet
class ShippingZone(models.Model):
    nickname = models.CharField(max_length=300, help_text="Nickname for admin use")

    code = models.CharField(
        max_length=3,
        validators=[alphanumeric],
        unique=True,
        help_text="The code is used to identify the right price in Stripe. Stripe product prices with metadata UK: 4.00 will be selected, for example.",
    )

    rate = MoneyField(
        verbose_name="Shipping fee",
        default=Money(0, "GBP"),
        max_digits=14,
        decimal_places=2,
        default_currency="GBP",
        null=False,
        blank=False,
        help_text="Per-delivery shipping fee",
    )

    rest_of_world = models.BooleanField(
        help_text="If selected, this zone's shipping rate will be used as the default shipping rate.",
        null=True,
        blank=True,
    )

    countries = CountryField(multiple=True, max_length=1000, blank=True)

    panels = [
        FieldPanel("nickname"),
        FieldPanel("code"),
        FieldPanel("rest_of_world"),
        FieldPanel("rate"),
        FieldPanel("countries", widget=forms.CheckboxSelectMultiple),
    ]

    def __str__(self) -> str:
        return f"[{self.code}] {self.nickname}"

    autocomplete_search_field = "nickname"

    def autocomplete_label(self):
        return str(self)

    @classmethod
    def get_for_country(self, iso_a2: str):
        # Check for a zone that has this code
        # If no zone, default to ROW pricing
        # settings.DEFAULT_SHIPPING_PRICE
        zone = (
            ShippingZone.objects.filter(countries__icontains=iso_a2)
            .order_by(Length("countries").asc())
            .first()
        )
        if zone is None:
            zone = ShippingZone.default_zone
        return zone

    @property
    def country_codes(self):
        included = []
        if len(self.countries) > 0:
            included = [c.code for c in self.countries]
        else:
            # ROW should exclude countries specified in other zones
            all_zones = ShippingZone.objects.all()
            countries_in_zones = {
                getattr(c, "code")
                for c in flatten_list(zone.countries for zone in list(all_zones))
            }
            included = [
                c for c in list(set(self.all_country_codes) - countries_in_zones)
            ]
        return list(set(included).intersection(set(self.stripe_allowed_countries)))

    def is_country_included(self, iso_a2: str) -> bool:
        return self.filter(countries__iexact=iso_a2) or self.code == self.row_code

    row_code = "ROW"

    @classmethod
    @property
    def default_zone(self):
        defined_row = ShippingZone.objects.filter(rest_of_world=True).first()
        if defined_row:
            if defined_row.code != self.row_code:
                defined_row.code = self.row_code
                defined_row.save()
            return defined_row
        return ShippingZone(
            nickname="Rest Of World",
            rest_of_world=True,
            code=self.row_code,
            countries=[],
        )

    @classmethod
    def get_for_code(cls, code: str):
        if code is not None:
            try:
                zone = ShippingZone.objects.get(code=code)
                return zone
            except:
                pass
        return ShippingZone.default_zone

    stripe_allowed_countries = [
        "AC",
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AL",
        "AM",
        "AO",
        "AQ",
        "AR",
        "AT",
        "AU",
        "AW",
        "AX",
        "AZ",
        "BA",
        "BB",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BL",
        "BM",
        "BN",
        "BO",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CK",
        "CL",
        "CM",
        "CN",
        "CO",
        "CR",
        "CV",
        "CW",
        "CY",
        "CZ",
        "DE",
        "DJ",
        "DK",
        "DM",
        "DO",
        "DZ",
        "EC",
        "EE",
        "EG",
        "EH",
        "ER",
        "ES",
        "ET",
        "FI",
        "FJ",
        "FK",
        "FO",
        "FR",
        "GA",
        "GB",
        "GD",
        "GE",
        "GF",
        "GG",
        "GH",
        "GI",
        "GL",
        "GM",
        "GN",
        "GP",
        "GQ",
        "GR",
        "GS",
        "GT",
        "GU",
        "GW",
        "GY",
        "HK",
        "HN",
        "HR",
        "HT",
        "HU",
        "ID",
        "IE",
        "IL",
        "IM",
        "IN",
        "IO",
        "IQ",
        "IS",
        "IT",
        "JE",
        "JM",
        "JO",
        "JP",
        "KE",
        "KG",
        "KH",
        "KI",
        "KM",
        "KN",
        "KR",
        "KW",
        "KY",
        "KZ",
        "LA",
        "LB",
        "LC",
        "LI",
        "LK",
        "LR",
        "LS",
        "LT",
        "LU",
        "LV",
        "LY",
        "MA",
        "MC",
        "MD",
        "ME",
        "MF",
        "MG",
        "MK",
        "ML",
        "MM",
        "MN",
        "MO",
        "MQ",
        "MR",
        "MS",
        "MT",
        "MU",
        "MV",
        "MW",
        "MX",
        "MY",
        "MZ",
        "NA",
        "NC",
        "NE",
        "NG",
        "NI",
        "NL",
        "NO",
        "NP",
        "NR",
        "NU",
        "NZ",
        "OM",
        "PA",
        "PE",
        "PF",
        "PG",
        "PH",
        "PK",
        "PL",
        "PM",
        "PN",
        "PR",
        "PS",
        "PT",
        "PY",
        "QA",
        "RE",
        "RO",
        "RS",
        "RU",
        "RW",
        "SA",
        "SB",
        "SC",
        "SE",
        "SG",
        "SH",
        "SI",
        "SJ",
        "SK",
        "SL",
        "SM",
        "SN",
        "SO",
        "SR",
        "SS",
        "ST",
        "SV",
        "SX",
        "SZ",
        "TA",
        "TC",
        "TD",
        "TF",
        "TG",
        "TH",
        "TJ",
        "TK",
        "TL",
        "TM",
        "TN",
        "TO",
        "TR",
        "TT",
        "TV",
        "TW",
        "TZ",
        "UA",
        "UG",
        "US",
        "UY",
        "UZ",
        "VA",
        "VC",
        "VE",
        "VG",
        "VN",
        "VU",
        "WF",
        "WS",
        "XK",
        "YE",
        "YT",
        "ZA",
        "ZM",
        "ZW",
        "ZZ",
    ]
    all_country_codes = list(
        set(dict(django_countries).keys()).intersection(set(stripe_allowed_countries))
    )
