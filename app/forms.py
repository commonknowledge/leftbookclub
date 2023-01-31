from typing import Any, Dict, List, Optional, Tuple

from dataclasses import dataclass

import stripe
from allauth.account.views import SignupForm
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.safestring import mark_safe
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from djstripe.enums import SubscriptionStatus

from app.models import User
from app.utils.stripe import (
    gift_giver_subscription_from_code,
    is_real_gift_code,
    is_redeemable_gift_code,
)


class MemberSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    gdpr_email_consent = forms.BooleanField(
        required=True,
        label="LBC can email me about my books and membership (required)",
    )
    # promotional_consent = forms.BooleanField(
    #     required=False,
    #     label="LBC can email me about special offers and promotions",
    # )

    field_order = [
        "email",
        # "email2",  # ignored when not present
        "first_name",
        "last_name",
        "password1",
        # "password2",  # ignored when not present
        "gdpr_email_consent",
        # "promotional_consent",
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
        if code is None or len(possible_codes) == 0:
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


class UpgradeAction(models.TextChoices):
    STATUS_QUO = "STATUS_QUO", "Your current plan"
    # ADD_SHIPPING = "ADD_SHIPPING", "Add shipping to your current plan"
    UPDATE_PRICE = (
        "UPDATE_PRICE",
        "Move to the new standard rate including shipping",
    )
    UPGRADE_TO_SOLIDARITY = "Upgrade to a Solidarity subscription"


@dataclass
class UpgradeOption:
    line_items: List[Dict[str, Any]]
    quote: Optional[stripe.Quote]
    label: Optional[str]
    title: str
    text: Any = ""
    action_text: str = "Select"
    default_selected: Optional[bool] = False


class UpgradeForm(forms.Form):
    choices = UpgradeAction
    user_id = forms.CharField(widget=forms.HiddenInput)
    fee_option = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=choices.choices,
        initial=choices.STATUS_QUO,
    )

    @classmethod
    def get_options_for_user(cls, user: User) -> Dict[UpgradeAction, UpgradeOption]:
        membership = user.get_membership_details()

        if (
            membership.subscription is None
            or membership.membership_plan_price is None
            or membership.membership_si is None
            or membership.subscription.is_gift_receiver
        ):
            raise ValueError("User is not a member yet.")

        if membership.shipping_zone is None:
            raise ValueError("Please add a shipping address first.")

        options: Dict[UpgradeAction, UpgradeOption] = {}

        if user.should_upgrade:
            new_items = membership.membership_plan_price.to_checkout_line_items(
                product=membership.membership_si.plan.product,
                zone=membership.shipping_zone,
            )

            quote = stripe.Quote.create(
                customer=user.stripe_customer.id,
                line_items=new_items,
            )

            # Remove old items
            if membership.membership_si is not None:
                new_items += [{"id": membership.membership_si.id, "deleted": True}]
            if membership.shipping_si is not None:
                new_items += [{"id": membership.shipping_si.id, "deleted": True}]

            old_price = float(membership.subscription.latest_invoice.amount_due)
            new_price = float(quote.amount_total / 100)
            effective_discount = abs((old_price - new_price) / old_price)

            ####
            ## Add status quo option
            ####
            title = f"Legacy fee ({effective_discount:.0%} discount)"

            if membership.shipping_si is None:
                title += "+ subsidised shipping"

            options[cls.choices.STATUS_QUO] = UpgradeOption(
                line_items=[],
                quote=None,
                title=title,
                label="Your current plan",
                text=f"""
                <p>You’re currently paying £{(membership.subscription.latest_invoice.amount_due)}{membership.membership_plan_price.humanised_interval()}. Select this option if it’s all you can afford right now — that is totally OK.</p>
                <p>Other members paying solidarity rates will make it possible for us to continue offering this, so please consider if you can afford to increase your rate or if you genuinely need to stay here.</p>
                """,
                action_text="Keep current plan",
                default_selected=True,
            )

            ####
            ## Add standard update option
            ####

            options[cls.choices.UPDATE_PRICE] = UpgradeOption(
                line_items=new_items,
                quote=quote,
                label="Recommended",
                title="2023 standard fee + pp",
                text=f"""
              <p>This is the price we are charging new members, which includes packaging and postage.</p>
              <p>If everyone paid this rate, we would break even.</p>
              """,
                action_text=f"Switch to £{(quote.amount_total / 100):.2f}{membership.membership_plan_price.humanised_interval()}",
                default_selected=True,
            )

        ####
        ## Add solidarity option
        ####
        from app.models import UpsellPlanSettings

        upsell_settings = UpsellPlanSettings.objects.filter(
            site=membership.membership_plan_price.plan.get_site()
        ).first()
        if upsell_settings is not None:
            solidarity_plan = upsell_settings.upsell_plan  # type: ignore
            if (
                solidarity_plan is not None
                and membership.membership_plan_price.plan.pk != solidarity_plan.pk
            ):
                if (
                    membership.membership_plan_price.plan.deliveries_per_year
                    != solidarity_plan.deliveries_per_year
                ):
                    # raise ValueError("Solidarity plan is not compatible with current plan")
                    pass
                else:
                    if membership.membership_plan_price.interval == "month":
                        new_price = solidarity_plan.monthly_price
                    else:
                        new_price = solidarity_plan.annual_price

                    new_items = new_price.to_checkout_line_items(
                        zone=membership.shipping_zone
                    )

                    quote = stripe.Quote.create(
                        customer=user.stripe_customer.id,
                        line_items=new_items,
                    )

                    # Remove old items
                    if membership.membership_si is not None:
                        new_items += [
                            {"id": membership.membership_si.id, "deleted": True}
                        ]
                    if membership.shipping_si is not None:
                        new_items += [
                            {"id": membership.shipping_si.id, "deleted": True}
                        ]

                    options[cls.choices.UPGRADE_TO_SOLIDARITY] = UpgradeOption(
                        line_items=new_items,
                        quote=quote,
                        label="If you can afford it",
                        title="2023 solidarity rate",
                        text="<p>Select this option if you can afford to pay a little more in order to support others on lower incomes.</p>",
                        action_text=f"Select (£{(quote.amount_total / 100):.2f})",
                    )

        return options

    def update_membership(self, *args, **kwargs):
        if not self.is_valid():
            raise ValueError("Form is not valid")
        fee_option = self.cleaned_data.get("fee_option")
        user = User.objects.get(pk=self.cleaned_data.get("user_id"))
        membership = user.get_membership_details()
        options = UpgradeForm.get_options_for_user(user)

        if (
            membership.subscription is None
            or membership.membership_plan_price is None
            or membership.membership_si is None
            or membership.subscription.is_gift_receiver
        ):
            raise ValueError("User is not a member yet.")

        if fee_option == UpgradeForm.choices.STATUS_QUO:
            pass
        elif (
            fee_option == UpgradeForm.choices.UPDATE_PRICE
            and options.get(UpgradeForm.choices.UPDATE_PRICE, None) is not None
        ):
            stripe.Subscription.modify(
                membership.subscription.id,
                proration_behavior="none",
                items=options[UpgradeForm.choices.UPDATE_PRICE].line_items,
            )
        elif (
            fee_option == UpgradeForm.choices.UPGRADE_TO_SOLIDARITY
            and options.get(UpgradeForm.choices.UPGRADE_TO_SOLIDARITY, None) is not None
        ):
            stripe.Subscription.modify(
                membership.subscription.id,
                proration_behavior="none",
                items=options[UpgradeForm.choices.UPDATE_PRICE].line_items,
            )
