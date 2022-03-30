from allauth.account.views import SignupForm
from django import forms
from django.contrib.auth import get_user_model


class MemberSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
