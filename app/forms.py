from allauth.account.views import SignupForm
from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget


class MemberSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)


class CountrySelectorForm(forms.Form):
    country = CountryField().formfield(widget=CountrySelectWidget)
