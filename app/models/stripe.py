import djstripe.models
import stripe
from django import forms
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Length
from django.forms import RadioSelect
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
    get_primary_product_for_djstripe_subscription,
    get_shipping_product_for_djstripe_subscription,
)


class LBCCustomer(djstripe.models.Customer):
    class Meta:
        proxy = True


add_proxy_method(djstripe.models.Customer, LBCCustomer, "lbc")


class LBCSubscription(djstripe.models.Subscription):
    class Meta:
        proxy = True

    def primary_product_name(self):
        primary_product = get_primary_product_for_djstripe_subscription(self)
        shipping_product = get_shipping_product_for_djstripe_subscription(self)
        if primary_product:
            if shipping_product:
                return f"{primary_product.name} + {shipping_product.name}"
            return primary_product.name

    def primary_product_id(self):
        primary_product = get_primary_product_for_djstripe_subscription(self)
        if primary_product:
            return primary_product.id

    def customer_id(self):
        return self.customer.id

    def is_gift_giver(self):
        self.metadata.get("gift_mode", None) is not None

    def is_gift_receiver(self):
        self.metadata.get("gift_giver_subscription", None) is not None

    def recipient_name(self):
        try:
            user = self.customer.subscriber
            return user.shipping_name()
        except:
            return None

    def recipient_email(self):
        try:
            user = self.customer.subscriber
            return user.primary_email
        except:
            return None

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
        return getattr(self, self.autocomplete_search_field)

    def get_prices_for_country(self, iso_a2: str, **kwargs):
        zone = ShippingZone.get_for_country(iso_a2)

        return djstripe.models.Price.objects.filter(
            product=self.id, active=True, metadata__shipping=zone.code, **kwargs
        ).order_by("unit_amount")

    def gift_giver_subscription(self):
        """
        If this subscription was created as a result of a neighbouring gift subscription
        """
        related_subscription_id = self.metadata.get("gift_giver_subscription", None)
        if related_subscription_id:
            return djstripe.models.Subscription.get(id=related_subscription_id)

    def current_book(self):
        from app.models.wagtail import BookPage

        book_types = self.metadata.get("book_types", None)
        if book_types is not None:
            book_types = book_types.split(",")
            return (
                BookPage.objects.filter(type__in=book_types)
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
