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
