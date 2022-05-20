from typing import Any, Dict, Optional

import stripe
from allauth.account.views import SignupForm
from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from djstripe.enums import SubscriptionStatus

from app.utils.stripe import (
    gift_giver_subscription_from_code,
    is_real_gift_code,
    is_redeemable_gift_code,
)


class MemberSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    gdpr_email_consent = forms.BooleanField(
        required=False,
        label="Can we email you with news and updates from the Left Book Club?",
    )

    field_order = [
        "email",
        "email2",  # ignored when not present
        "first_name",
        "last_name",
        "password1",
        "password2",  # ignored when not present
        "gdpr_email_consent",
        "terms_and_conditions",
    ]

    def save(self, request):
        user = super().save(request)
        user.gdpr_email_consent = self.cleaned_data.get("gdpr_email_consent", False)
        user.save()
        return user


class CountrySelectorForm(forms.Form):
    country = CountryField().formfield(
        label="Shipping country", widget=CountrySelectWidget
    )


class GiftCodeForm(forms.Form):
    code = forms.CharField(label="Enter your gift code", max_length=12)

    def clean(self) -> Optional[Dict[str, Any]]:
        cleaned_data = super().clean()
        code = cleaned_data.get("code")
        possible_codes = stripe.PromotionCode.list(code=code).data
        if len(possible_codes) == 0:
            raise ValidationError("This isn't a real code")
        if not possible_codes[0].metadata.get("gift_giver_subscription", False):
            raise ValidationError(
                "This is a normal promo code, not a gift card code. To use this code, pick a membership plan from the homepage and enter the code in the checkout/payment page."
            )
        if not is_redeemable_gift_code(code):
            if is_real_gift_code(code):
                raise ValidationError("This gift code has already been redeemed")
            else:
                raise ValidationError("This gift code isn't valid")
        gift_giver_subscription = gift_giver_subscription_from_code(code)
        if gift_giver_subscription is None:
            raise ValidationError(
                "This is a normal promo code. Select a plan to apply it."
            )

        if gift_giver_subscription.status != SubscriptionStatus.active:
            raise ValidationError(
                "This gift card isn't valid anymore because the gift giver stopped paying for it."
            )


class StripeShippingForm(forms.Form):
    name = forms.CharField(label="Recipient name", max_length=250)
    line1 = forms.CharField(
        label="Address line 1",
        help_text="Address line 1 (e.g., street, PO Box, or company name)",
        max_length=250,
        required=False,
        empty_value=None,
    )
    line2 = forms.CharField(
        label="Address line 2",
        help_text="Address line 2 (e.g., apartment, suite, unit, or building)",
        max_length=250,
        required=False,
        empty_value=None,
    )
    postal_code = forms.CharField(
        label="Post code",
        help_text="ZIP or postal code",
        max_length=250,
        required=False,
        empty_value=None,
    )
    city = forms.CharField(
        label="City",
        help_text="City, district, suburb, town, or village",
        max_length=250,
        required=False,
        empty_value=None,
    )
    state = forms.CharField(
        label="Region",
        help_text="Region, state, county, province",
        max_length=250,
        required=False,
        empty_value=None,
    )
    country = CountryField().formfield(
        label="Country",
        help_text="Country",
        widget=CountrySelectWidget,
        required=False,
        empty_value=None,
    )

    @classmethod
    def stripe_data_to_initial(cls, stripe_data) -> dict:
        return {
            "name": stripe_data.get("name", None),
            "line1": stripe_data.get("address", {}).get("line1", None),
            "line2": stripe_data.get("address", {}).get("line2", None),
            "postal_code": stripe_data.get("address", {}).get("postal_code", None),
            "city": stripe_data.get("address", {}).get("city", None),
            "state": stripe_data.get("address", {}).get("state", None),
            "country": stripe_data.get("address", {}).get("country", None),
        }

    @classmethod
    def form_data_to_stripe(cls, cleaned_data) -> dict:
        return {
            "name": cleaned_data["name"],
            "address": {
                "line1": cleaned_data.get("line1", None),
                "line2": cleaned_data.get("line2", None),
                "postal_code": cleaned_data.get("postal_code", None),
                "city": cleaned_data.get("city", None),
                "state": cleaned_data.get("state", None),
                "country": cleaned_data.get("country", None),
            },
        }

    def to_stripe(self) -> dict:
        return StripeShippingForm.form_data_to_stripe(self.cleaned_data)
