from typing import Any, Dict, Optional

from allauth.account.views import SignupForm
from django import forms
from django.core.exceptions import ValidationError
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from app.utils.stripe import is_real_gift_code, is_redeemable_gift_code


class MemberSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)


class CountrySelectorForm(forms.Form):
    country = CountryField().formfield(
        label="Shipping country", widget=CountrySelectWidget
    )


class GiftCodeForm(forms.Form):
    code = forms.CharField(label="Enter your gift code", max_length=12)

    def clean(self) -> Optional[Dict[str, Any]]:
        cleaned_data = super().clean()
        code = cleaned_data.get("code")
        if not is_redeemable_gift_code(code):
            if is_real_gift_code(code):
                raise ValidationError("This gift code has already been redeemed")
            else:
                raise ValidationError("This gift code isn't valid")


class StripeShippingForm(forms.Form):
    name = forms.CharField(label="Recipient name", max_length=250)
    line1 = forms.CharField(
        label="Address line 1 (e.g., street, PO Box, or company name)",
        max_length=250,
        required=False,
        empty_value=None,
    )
    line2 = forms.CharField(
        label="Address line 2 (e.g., apartment, suite, unit, or building)",
        max_length=250,
        required=False,
        empty_value=None,
    )
    postal_code = forms.CharField(
        label="ZIP or postal code", max_length=250, required=False, empty_value=None
    )
    city = forms.CharField(
        label="City, district, suburb, town, or village",
        max_length=250,
        required=False,
        empty_value=None,
    )
    state = forms.CharField(
        label="State, county, province, or region",
        max_length=250,
        required=False,
        empty_value=None,
    )
    country = CountryField().formfield(
        label="Country", widget=CountrySelectWidget, required=False, empty_value=None
    )

    def clean(self):
        self.cleaned_data = super().clean()
        self.cleaned_data["shipping"] = {
            "name": self.cleaned_data["name"],
            "address": {
                "line1": self.cleaned_data("line1", None),
                "line2": self.cleaned_data("line2", None),
                "postal_code": self.cleaned_data("postal_code", None),
                "city": self.cleaned_data("city", None),
                "state": self.cleaned_data("state", None),
                "country": self.cleaned_data("country", None),
            },
        }
        return self.cleaned_data
