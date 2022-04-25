import djstripe.models
import stripe
from django import forms
from django.core.validators import RegexValidator
from django.db import models
from django.forms import RadioSelect
from django.utils.translation import gettext_lazy as _
from django_countries import countries as django_countries
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from djmoney.models.fields import MoneyField
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.snippets.models import register_snippet

from app.utils import flatten_list


class LBCCustomer(djstripe.models.Customer):
    class Meta:
        proxy = True


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


alphanumeric = RegexValidator(
    r"^[0-9a-zA-Z]*$", "Only alphanumeric characters are allowed."
)


@register_snippet
class ShippingZone(models.Model):
    # class CountriesMode(models.TextChoices):
    #     INCLUDE = 'INCLUDE', _('Include countries')
    #     EXCLUDE = 'EXCLUDE', _('Exclude countries')

    nickname = models.CharField(max_length=300, help_text="Nickname for admin use")
    code = models.CharField(
        max_length=3,
        validators=[alphanumeric],
        unique=True,
        help_text="The code is used to identify the right price in Stripe. Stripe product prices with metadata UK: 4.00 will be selected, for example.",
    )
    # rate = MoneyField(max_digits=14, decimal_places=2, default_currency='GBP', null=False, blank=False)
    # countries_mode = models.CharField(
    #   max_length=10,
    #   choices=CountriesMode.choices,
    #   default=CountriesMode.INCLUDE,
    #   help_text="Should the countries here be excluded from the full list (e.g. rest of world) or included? (e.g. EU)"
    # )
    countries = CountryField(multiple=True)

    panels = [
        FieldPanel("nickname"),
        FieldPanel("code"),
        FieldPanel("countries", widget=forms.CheckboxSelectMultiple),
    ]

    def __str__(self) -> str:
        return f"[{self.code}] {self.nickname}"

    @classmethod
    def get_for_country(self, iso_a2: str):
        # Check for a zone that has this code
        # If no zone, default to ROW pricing
        # settings.DEFAULT_SHIPPING_PRICE
        zone = ShippingZone.objects.filter(countries__icontains=iso_a2).first()
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
        return ShippingZone(nickname="Rest Of World", code=self.row_code, countries=[])

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
