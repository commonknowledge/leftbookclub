from typing import Any, Dict, List, Optional, Tuple

from dataclasses import dataclass
from datetime import datetime

import djstripe.models
import stripe
from allauth.account.views import SignupForm
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.template import Context, Template
from django.utils.safestring import mark_safe
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from djstripe.enums import SubscriptionStatus

from app import analytics
from app.models import MembershipPlanPage, User
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
    title: str
    line_items: List[Dict[str, Any]]
    price_float: float
    price_str: str
    interval: str
    interval_count: int
    plan: MembershipPlanPage
    product: Optional[djstripe.models.Product] = None
    old_price_float: Optional[float] = None
    old_price_str: Optional[str] = None
    old_interval: Optional[str] = None
    old_interval_count: Optional[int] = None
    old_plan: Optional[MembershipPlanPage] = None
    old_product: Optional[djstripe.models.Product] = None
    text: Any = ""
    action_text: str = "Select"
    label: Optional[str] = None
    discount: Optional[str] = None
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
        if (
            user.active_subscription is None
            or user.active_subscription.membership_plan_price is None
            or user.active_subscription.membership_si is None
            or user.active_subscription.is_gift_receiver
        ):
            raise ValueError("User is not a member yet.")

        if user.active_subscription.shipping_zone is None:
            raise ValueError("Please add a shipping address first.")

        year = datetime.now().year

        options: Dict[UpgradeAction, UpgradeOption] = {}

        title = f"Your current plan"
        old_price = user.active_subscription.next_fee
        old_price_str = f"£{(old_price):.2f}{user.active_subscription.membership_plan_price.humanised_interval()}"

        status_quo_data = dict(
            old_price_float=old_price,
            old_price_str=old_price_str,
            old_interval=user.active_subscription.membership_plan_price.interval,
            old_interval_count=user.active_subscription.membership_plan_price.interval_count,
            old_plan=user.active_subscription.membership_plan_price.plan,
            old_product=user.active_subscription.primary_product,
        )

        if not user.active_subscription.should_upgrade:
            options[cls.choices.STATUS_QUO] = UpgradeOption(
                line_items=[],
                plan=user.active_subscription.membership_plan_price.plan,
                price_float=old_price,
                price_str=old_price_str,
                interval=user.active_subscription.membership_plan_price.interval,
                interval_count=user.active_subscription.membership_plan_price.interval_count,
                product=user.active_subscription.primary_product,
                **status_quo_data,
                title=title,
                label="Your current plan",
                text=user.active_subscription.membership_plan_price.description,
                action_text="Keep current plan",
                default_selected=True,
            )

            # TODO: Add product selection to the current plan
            # for when MembershipPlanPrice has multiple products
            #
            # for plan in MembershipPlanPage.objects.public().live().all():
            #     if plan == user.active_subscription.membership_plan_price.plan:
            #         continue

            #     if user.active_subscription.membership_plan_price.interval == "month":
            #         plan_price = plan.monthly_price
            #     else:
            #         plan_price = plan.annual_price

            #     new_price = float(plan_price.price_including_shipping(user.active_subscription.shipping_zone).amount)
            #     new_price_str = f"£{(new_price):.2f}{plan_price.humanised_interval()}"

            #     # Create a new option for this alternative plan
            #     options[plan_price.id] = UpgradeOption(
            #         line_items=plan_price.to_checkout_line_items(
            #             zone=user.active_subscription.shipping_zone,
            #         ),
            #         plan=plan,
            #         price_float=new_price,
            #         price_str=new_price_str,
            #         title=plan.title,
            #         text=plan_price.description,
            #         action_text="Switch",
            #     )
        else:
            new_items = (
                user.active_subscription.membership_plan_price.to_checkout_line_items(
                    product=user.active_subscription.membership_si.plan.product,
                    zone=user.active_subscription.shipping_zone,
                )
            )

            # Remove old items
            if user.active_subscription.membership_si is not None:
                new_items += [
                    {"id": user.active_subscription.membership_si.id, "deleted": True}
                ]
            if user.active_subscription.shipping_si is not None:
                new_items += [
                    {"id": user.active_subscription.shipping_si.id, "deleted": True}
                ]

            new_price = float(user.active_subscription.membership_plan_price.price_including_shipping(user.active_subscription.shipping_zone).amount)  # type: ignore
            new_price_str = f"£{(new_price):.2f}{user.active_subscription.membership_plan_price.humanised_interval()}"
            effective_discount = abs((old_price - new_price) / old_price)

            ####
            ## Add status quo option
            ####

            if user.active_subscription.has_legacy_membership_price:
                title = f"Legacy rate"

            # if user.active_subscription.shipping_si is None:
            #     title += " with unpaid shipping"

            from app.models import UpsellPlanSettings

            upsell_settings = UpsellPlanSettings.objects.first()
            if upsell_settings is not None:
                settings_text = upsell_settings.upgrade_membership_text

            template = Template(settings_text)
            context = Context({"old_price": old_price_str})

            options[cls.choices.STATUS_QUO] = UpgradeOption(
                line_items=[],
                plan=user.active_subscription.membership_plan_price.plan,
                price_float=old_price,
                price_str=old_price_str,
                interval=user.active_subscription.membership_plan_price.interval,
                interval_count=user.active_subscription.membership_plan_price.interval_count,
                product=user.active_subscription.primary_product,
                **status_quo_data,
                discount=f"{effective_discount:.0%}",
                title=title,
                label="Your current plan",
                text=template.render(context),
                action_text=f"Continue with {old_price_str}",
            )

            ####
            ## Add standard update option
            ####

            title = f"{year} standard rate"
            # if user.active_subscription.shipping_si is None:
            #     title += " including shipping"

            raw_price_string = (
                user.active_subscription.membership_plan_price.raw_price_string()
            )
            shipping_price_string = (
                user.active_subscription.membership_plan_price.shipping_price_string(
                    user.active_subscription.shipping_zone
                )
            )

            options[cls.choices.UPDATE_PRICE] = UpgradeOption(
                line_items=new_items,
                plan=user.active_subscription.membership_plan_price.plan,
                price_float=new_price,
                price_str=new_price_str,
                interval=user.active_subscription.membership_plan_price.interval,
                interval_count=user.active_subscription.membership_plan_price.interval_count,
                product=user.active_subscription.primary_product,
                **status_quo_data,
                label="Recommended plan",
                title=title,
                text=f"""
                  <p>This is what we are charging new members. If everyone paid this rate, we would break even.</p>
                  <ul>
                  <li><b>{raw_price_string}</b> for membership (including books, community and benefits)</li>
                  <li><b>{shipping_price_string}</b> for packaging + postage</li>
                  </ul>
                """,
                action_text=f"Switch to {new_price_str}",
                default_selected=True,
            )

            ####
            ## Add solidarity option
            ####
            from app.models import UpsellPlanSettings

            upsell_settings = UpsellPlanSettings.objects.first()
            if upsell_settings is not None:
                solidarity_plan = upsell_settings.upsell_plan  # type: ignore
                if (
                    solidarity_plan is not None
                    and user.active_subscription.membership_plan_price.plan.pk
                    != solidarity_plan.pk
                ):
                    if (
                        user.active_subscription.membership_plan_price.plan.deliveries_per_year
                        != solidarity_plan.deliveries_per_year
                    ):
                        # raise ValueError("Solidarity plan is not compatible with current plan")
                        pass
                    else:
                        if (
                            user.active_subscription.membership_plan_price.interval
                            == "month"
                        ):
                            plan_price = solidarity_plan.monthly_price
                        else:
                            plan_price = solidarity_plan.annual_price

                        new_items = plan_price.to_checkout_line_items(
                            zone=user.active_subscription.shipping_zone
                        )

                        new_price = float(plan_price.price_including_shipping(user.active_subscription.shipping_zone).amount)  # type: ignore
                        new_price_str = plan_price.price_string_including_shipping(
                            user.active_subscription.shipping_zone
                        )
                        raw_price_string = plan_price.raw_price_string()
                        shipping_price_string = plan_price.shipping_price_string(
                            user.active_subscription.shipping_zone
                        )

                        # Remove old items
                        if user.active_subscription.membership_si is not None:
                            new_items += [
                                {
                                    "id": user.active_subscription.membership_si.id,
                                    "deleted": True,
                                }
                            ]
                        if user.active_subscription.shipping_si is not None:
                            new_items += [
                                {
                                    "id": user.active_subscription.shipping_si.id,
                                    "deleted": True,
                                }
                            ]

                        options[cls.choices.UPGRADE_TO_SOLIDARITY] = UpgradeOption(
                            line_items=new_items,
                            plan=solidarity_plan,
                            price_float=new_price,
                            price_str=new_price_str,
                            interval=user.active_subscription.membership_plan_price.interval,
                            interval_count=user.active_subscription.membership_plan_price.interval_count,
                            product=plan_price.default_product(),
                            **status_quo_data,
                            # label="If you can afford it",
                            title=f"{year} solidarity rate",
                            text=f"""
                            <p>Select this option if you can afford to pay a little more in order to support others on lower incomes.</p>
                            <ul>
                            <li><b>{raw_price_string}</b> for membership (including books, community and benefits)</li>
                            <li><b>{shipping_price_string}</b> for packaging + postage</li>
                            </ul>
                            """,
                            action_text=f"Switch to {new_price_str}",
                        )

        return options

    def update_subscription(self, *args, **kwargs):
        if not self.is_valid():
            raise ValueError("Form is not valid")
        fee_option: UpgradeForm.choices = self.cleaned_data.get("fee_option")
        user = User.objects.get(pk=self.cleaned_data.get("user_id"))
        options = UpgradeForm.get_options_for_user(user)

        if (
            user.active_subscription is None
            or user.active_subscription.membership_plan_price is None
            or user.active_subscription.membership_si is None
            or user.active_subscription.is_gift_receiver
        ):
            raise ValueError("User is not a member yet.")

        upgrade_status_quo_month_year = (
            f"UPGRADE_STATUS_QUO_CHOSEN_{datetime.now().strftime('%Y-%m')}"
        )
        upgrade_recommended_month_year = (
            f"UPGRADE_RECOMMENDED_OPTION_CHOSEN_{datetime.now().strftime('%Y-%m')}"
        )
        upgrade_solidarity_month_year = (
            f"UPGRADE_SOLIDARITY_OPTION_CHOSEN_{datetime.now().strftime('%Y-%m')}"
        )

        if fee_option == UpgradeForm.choices.STATUS_QUO:
            upgrade_option = options[fee_option]
            try:
                analytics.upgrade_remain_on_current_plan(
                    user,
                    campaign="UpgradeForm",
                    old_amount=upgrade_option.old_price_float,
                    old_interval=upgrade_option.old_interval,
                    old_interval_count=upgrade_option.old_interval_count,
                    old_plan=upgrade_option.old_plan.title,
                    old_product=upgrade_option.old_product.name,
                )
            except Exception as e:
                if settings.DEBUG:
                    raise e
                print("Error sending analytics event: upgrade_remain_on_current_plan")
                print(e)
                pass
            return user.active_subscription
        elif (
            fee_option == UpgradeForm.choices.UPDATE_PRICE
            and options.get(UpgradeForm.choices.UPDATE_PRICE, None) is not None
        ):
            upgrade_option = options[fee_option]
            subscription = stripe.Subscription.modify(
                user.active_subscription.id,
                proration_behavior="none",
                items=options[fee_option].line_items,
            )
            try:
                analytics.upgrade(
                    user,
                    campaign="UpgradeForm",
                    option_title=upgrade_option.title,
                    old_amount=upgrade_option.old_price_float,
                    old_interval=upgrade_option.old_interval,
                    old_interval_count=upgrade_option.old_interval_count,
                    old_plan=upgrade_option.old_plan.title,
                    old_product=upgrade_option.old_product.name,
                    new_amount=upgrade_option.price_float,
                    new_interval=upgrade_option.interval,
                    new_interval_count=upgrade_option.interval_count,
                    new_plan=upgrade_option.plan.title,
                    new_product=upgrade_option.product.name,
                )
            except Exception as e:
                if settings.DEBUG:
                    raise e
                print("Error sending analytics event: upgrade_remain_on_current_plan")
                print(e)
                pass

            sub = djstripe.models.Subscription.sync_from_stripe_data(subscription)
            return sub.lbc()
        elif (
            fee_option == UpgradeForm.choices.UPGRADE_TO_SOLIDARITY
            and options.get(UpgradeForm.choices.UPGRADE_TO_SOLIDARITY, None) is not None
        ):
            upgrade_option = options[fee_option]

            subscription = stripe.Subscription.modify(
                user.active_subscription.id,
                proration_behavior="none",
                items=upgrade_option.line_items,
            )

            try:
                analytics.upgrade(
                    user,
                    campaign="UpgradeForm",
                    option_title=upgrade_option.title,
                    old_amount=upgrade_option.old_price_float,
                    old_interval=upgrade_option.old_interval,
                    old_interval_count=upgrade_option.old_interval_count,
                    old_plan=upgrade_option.old_plan,
                    old_product=upgrade_option.old_product.name,
                    new_amount=upgrade_option.price_float,
                    new_interval=upgrade_option.interval,
                    new_interval_count=upgrade_option.interval_count,
                    new_plan=upgrade_option.plan,
                    new_product=upgrade_option.product.name,
                )
            except Exception as e:
                if settings.DEBUG:
                    raise e
                print("Error sending analytics event: upgrade_remain_on_current_plan")
                print(e)
                pass

            sub = djstripe.models.Subscription.sync_from_stripe_data(subscription)
            return sub.lbc()


# Create a form with a field for user_id, donation_amount, and on submission add a donation product to the subscription
class DonationForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    donation_amount = forms.DecimalField(
        min_value=0,
        max_value=1000,
        decimal_places=2,
        localize=True,
        label="Donation amount",
        help_text="Enter a donation amount in GBP",
    )

    def update_subscription(self, *args, **kwargs):
        if not self.is_valid():
            raise ValueError("Form is not valid")
        user = User.objects.get(pk=self.cleaned_data.get("user_id"))
        new_amount = self.cleaned_data.get("donation_amount")

        if (
            user.active_subscription is None
            or user.active_subscription.is_gift_receiver
        ):
            raise ValueError("No billable subscription was found for this user.")

        old_amount = None
        if user.active_subscription.donation_si is not None:
            old_amount = user.active_subscription.donation_si.plan.amount

        # Create a new donation product
        sub = user.active_subscription.upsert_regular_donation(
            float(new_amount), metadata={"via": "donation_form"}
        )

        if new_amount > 0:
            analytics.donate(
                user,
                new_amount=float(new_amount),
                old_amount=float(old_amount) if old_amount is not None else None,
            )
        else:
            analytics.donation_ended(
                user, old_amount=float(old_amount) if old_amount is not None else None
            )

        return sub


import re
import uuid

from django_dbq.models import Job


class BatchUpdateSubscriptionsForm(forms.Form):
    subscription_ids = forms.CharField(
        widget=forms.Textarea,
        help_text="List of IDs separated by new lines, commas, or spaces",
    )
    add_or_update_shipping = forms.BooleanField(required=False)
    optional_custom_shipping_fee = forms.DecimalField(
        min_value=0,
        max_value=1000,
        decimal_places=2,
        localize=True,
        required=False,
    )
    update_membership_fee = forms.BooleanField(required=False)
    optional_custom_membership_fee = forms.DecimalField(
        min_value=0,
        max_value=1000,
        decimal_places=2,
        localize=True,
        required=False,
    )
    batch_id = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)

    proration_behavior = forms.ChoiceField(
        required=False,
        choices=[
            ("create_prorations", "create_prorations"),
            ("none", "none"),
            ("always_invoice", "always_invoice"),
        ],
        initial="none",
        help_text="""
          Determines how to handle prorations resulting from the billing_cycle_anchor. If no value is passed, the default is `create_prorations`. Options are:
          - `create_prorations`: Will cause proration invoice items to be created when applicable.
          - `none`: Disable creating prorations in this request.
          - `always_invoice`: Will create proration invoice items that will be invoiced immediately, and then invoice immediately.
        """,
    )

    def process_request(self, *args, **kwargs):
        if not self.is_valid():
            raise ValueError("Form is not valid")

        batch_id = str(self.cleaned_data.get("batch_id"))
        subscription_ids = self.cleaned_data.get("subscription_ids")
        add_or_update_shipping = self.cleaned_data.get("add_or_update_shipping")
        optional_custom_shipping_fee = self.cleaned_data.get(
            "optional_custom_shipping_fee"
        )
        update_membership_fee = self.cleaned_data.get("update_membership_fee")
        optional_custom_membership_fee = self.cleaned_data.get(
            "optional_custom_membership_fee"
        )
        proration_behavior = self.cleaned_data.get("proration_behavior")

        # Split by comma, space, or new line
        subscription_ids = re.split(r"[\s,]+", subscription_ids)

        # Create jobs for each subscription ID
        for subscription_id in subscription_ids:
            if add_or_update_shipping or update_membership_fee:
                Job.objects.create(
                    name="update_subscription",
                    workspace={
                        "batch_id": batch_id,
                        "subscription_id": subscription_id.strip(),
                        "proration_behavior": proration_behavior,
                        "add_or_update_shipping": add_or_update_shipping,
                        "optional_custom_shipping_fee": float(
                            optional_custom_shipping_fee
                        )
                        if add_or_update_shipping
                        and optional_custom_shipping_fee is not None
                        and optional_custom_shipping_fee != ""
                        else None,
                        "update_membership_fee": update_membership_fee,
                        "optional_custom_membership_fee": float(
                            optional_custom_membership_fee
                        )
                        if update_membership_fee
                        and optional_custom_membership_fee is not None
                        and optional_custom_membership_fee != ""
                        else None,
                    },
                )


### V2 flow forms


class SelectDeliveriesForm(forms.Form):
    delivery_plan_id = forms.CharField(widget=forms.HiddenInput)


class SelectSyllabusForm(forms.Form):
    syllabus_id = forms.CharField(widget=forms.HiddenInput)


class SelectPaymentPlanForm(forms.Form):
    payment_plan_id = forms.CharField(widget=forms.HiddenInput)
