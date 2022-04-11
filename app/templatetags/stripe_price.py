from django import template
from django.template.defaultfilters import stringfilter
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from djstripe.utils import CURRENCY_SIGILS

register = template.Library()


def get_friendly_currency_amount(amount, currency: str = "GBP") -> str:
    currency = currency.upper()
    sigil = CURRENCY_SIGILS.get(currency, "")
    return f"{sigil}{amount:.2f}"


@register.filter
def stripe_price(self):
    try:
        if isinstance(self, str):
            return self
        if self.billing_scheme == "per_unit":
            unit_amount = self.unit_amount / 100
            amount = get_friendly_currency_amount(unit_amount, self.currency)
        else:
            # tiered billing scheme
            tier_1 = self.tiers[0]
            flat_amount_tier_1 = tier_1["flat_amount"]
            formatted_unit_amount_tier_1 = get_friendly_currency_amount(
                tier_1["unit_amount"] / 100, self.currency
            )
            amount = f"Starts at {formatted_unit_amount_tier_1} per unit"

            # stripe shows flat fee even if it is set to 0.00
            if flat_amount_tier_1 is not None:
                formatted_flat_amount_tier_1 = get_friendly_currency_amount(
                    flat_amount_tier_1 / 100, self.currency
                )
                amount = f"{amount} + {formatted_flat_amount_tier_1}"

        format_args = {"amount": amount}

        if self.recurring:
            interval_count = self.recurring["interval_count"]
            if interval_count == 1:
                interval = {
                    "day": _("day"),
                    "week": _("week"),
                    "month": _("month"),
                    "year": _("year"),
                }[self.recurring["interval"]]
                template = _("{amount}/{interval}")
                format_args["interval"] = interval
            else:
                interval = {
                    "day": _("days"),
                    "week": _("weeks"),
                    "month": _("months"),
                    "year": _("years"),
                }[self.recurring["interval"]]
                template = _("{amount} / every {interval_count} {interval}")
                format_args["interval"] = interval
                format_args["interval_count"] = interval_count

        else:
            template = _("{amount} (one time)")

        return format_lazy(template, **format_args)
    except:
        return None
