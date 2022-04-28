from typing import Any, Dict

import urllib.parse
from datetime import datetime
from importlib.metadata import metadata
from multiprocessing.sharedctypes import Value
from pipes import Template
from urllib.parse import urlencode

import djstripe.models
import stripe
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import include, path, re_path, reverse, reverse_lazy
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.edit import FormView
from djmoney.money import Money
from djstripe import settings as djstripe_settings

from app.forms import CountrySelectorForm, GiftCodeForm, StripeShippingForm
from app.models import LBCProduct
from app.models.stripe import ShippingZone
from app.utils.stripe import create_gift, gift_giver_subscription_from_code


class MemberSignupUserRegistrationMixin(LoginRequiredMixin):
    login_url = reverse_lazy("account_signup")


class CreateCheckoutSessionView(MemberSignupUserRegistrationMixin, TemplateView):
    template_name = "stripe/checkout.html"
    context = {}

    def get_context_data(self, **kwargs):
        """
        Creates and returns a Stripe Checkout Session
        """

        # get the id of the Model instance of djstripe_settings.djstripe_settings.get_subscriber_model()
        # here we have assumed it is the Django User model. It could be a Team, Company model too.
        # note that it needs to have an email field.
        user = self.request.user

        # example of how to insert the SUBSCRIBER_CUSTOMER_KEY: id in the metadata
        # to add customer.subscriber to the newly created/updated customer.
        session_args = self.context
        session_args["metadata"] = self.context.get("metadata", {})
        session_args["metadata"][
            djstripe_settings.djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
        ] = user.id

        try:
            additional_args = {}
            # retreive the Stripe Customer.
            customer, is_new = user.get_or_create_customer()
            if customer is not None:
                additional_args["customer"] = customer.id
            elif user.primary_email is not None:
                additional_args["customer_email"] = user.primary_email

            # ! Note that Stripe will always create a new Customer Object if customer id not provided
            # ! even if customer_email is provided!
            session = stripe.checkout.Session.create(**session_args, **additional_args)

        except djstripe.models.Customer.DoesNotExist:
            session = stripe.checkout.Session.create(**session_args)

        return {
            **super().get_context_data(**kwargs),
            "CHECKOUT_SESSION_ID": session.id,
            "STRIPE_PUBLIC_KEY": djstripe.settings.djstripe_settings.STRIPE_PUBLIC_KEY,
        }


class MemberSignupCompleteView(MemberSignupUserRegistrationMixin, TemplateView):
    template_name = "app/welcome.html"

    def get_context_data(self, *args, **kwargs):
        # Get parent Context
        page_context = super().get_context_data(**kwargs)
        session_id = self.request.GET.get("session_id", None)
        gift_mode = False
        session = None
        customer = None
        subscription = None

        if session_id is not None:
            session = stripe.checkout.Session.retrieve(session_id)
            customer_from_stripe = stripe.Customer.retrieve(session.customer)
            (
                customer,
                is_new,
            ) = djstripe.models.Customer._get_or_create_from_stripe_object(
                customer_from_stripe
            )
            subscription = stripe.Subscription.retrieve(session.subscription)
            gift_mode = session.metadata.get("gift_mode", None)

        membership_context = {}

        # try:
        if (
            gift_mode is not None
            and gift_mode is not False
            and session is not None
            and subscription is not None
            and customer is not None
        ):
            """
            Resolve gift purchase by creating a promo code and relating it to the gift buyer's subscription,
            for future reference.
            """
            print("gift_mode!!!")
            membership_context = self.finish_gift_purchase(
                session, subscription, customer
            )
        elif session is not None and subscription is not None and customer is not None:
            """
            Resolve a normal membership purchase
            """
            membership_context = self.finish_self_purchase(
                session, subscription, customer
            )
        # except Exception as error:
        #     page_context['error'] = str(error)

        page_context = {**page_context, **membership_context}

        # Sync Stripe data to Django
        self.request.user.refresh_stripe_data()

        return page_context

    def finish_self_purchase(self, session, subscription, customer) -> dict:
        # Relate the django user to this customer
        customer.subscriber = self.request.user
        customer.save()

        # Delete old subscriptions
        self.request.user.cleanup_membership_subscriptions(keep=[subscription.id])

        return {}

    def finish_gift_purchase(self, session, gift_giver_subscription, customer) -> dict:
        page_context = {}
        page_context[
            "gift_giver_subscription"
        ] = djstripe.models.Subscription.sync_from_stripe_data(gift_giver_subscription)
        page_context["gift_mode"] = True
        promo_code_id = gift_giver_subscription.metadata.get("promo_code", None)
        if promo_code_id is not None:
            # Refreshed the page -- don't let them generate a new coupon each time they do that!
            promo_code = stripe.PromotionCode.retrieve(promo_code_id)
            page_context["promo_code"] = promo_code.code
        else:
            # First time
            gift_giver_subscription = stripe.Subscription.modify(
                session.subscription, metadata={"gift_mode": True}
            )
            # 2. Generate coupon
            product_id = gift_giver_subscription.get("items").data[0].price.product
            coupon = stripe.Coupon.create(
                applies_to={"products": [product_id]},
                percent_off=100,
                duration="forever",
            )
            promo_code = stripe.PromotionCode.create(
                coupon=coupon.id,
                max_redemptions=1,
                metadata={
                    "gift_giver_subscription": session.subscription,
                    "related_django_user": self.request.user.id,
                },
            )
            page_context["promo_code"] = promo_code.code

            gift_giver_subscription = stripe.Subscription.modify(
                session.subscription,
                metadata={"promo_code": promo_code.id},
            )

            djstripe.models.Subscription.sync_from_stripe_data(gift_giver_subscription)
            page_context["gift_giver_subscription"] = gift_giver_subscription

            # Send them this promo code via email
            redeem_url = self.request.build_absolute_uri(
                reverse("redeem", kwargs={"code": promo_code.code})
            )
            send_mail(
                "Your Left Book Club Gift Code",
                f"Your gift code is {promo_code.code}. It can be redeemed at {redeem_url}",
                "noreply@leftbookclub.com",
                [self.request.user.email],
                html_message=render_to_string(
                    template_name="app/emails/send_gift_code.html",
                    context={
                        "user": self.request.user,
                        "promo_code": promo_code.code,
                    },
                ),
            )

        return page_context


class LoginRequiredTemplateView(LoginRequiredMixin, TemplateView):
    pass


class StripeCustomerPortalView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, **kwargs):
        return_url = self.request.build_absolute_uri(reverse("account_membership"))
        session = stripe.billing_portal.Session.create(
            customer=self.request.user.stripe_customer.id,
            return_url=return_url,
        )
        return session.url


class CartOptionsView(TemplateView):
    template_name = "app/frames/cart_options.html"
    url_pattern = "cartoptions/<product_id>/"

    def get_context_data(self, product_id=None, **kwargs):
        from .models import BookPage

        context = super().get_context_data(**kwargs)
        product = BookPage.objects.get(shopify_product_id=product_id)
        context = {
            **context,
            "product": product.latest_shopify_product,
            "disabled": self.request.GET.get("disabled") == "True",
        }

        return context


class GiftCodeRedeemView(FormView):
    template_name = "app/redeem.html"
    form_class = GiftCodeForm
    success_url = reverse_lazy("redeem_setup")

    url_params = "<code>/"

    def get_initial(self, *args, **kwargs):
        code = self.kwargs.get("code", None)
        if code is not None:
            return {"code": code}
        else:
            return super().get_initial()

    def form_valid(self, form):
        gift_giver_subscription = gift_giver_subscription_from_code(
            form.cleaned_data["code"]
        )
        if gift_giver_subscription is None:
            raise ValueError("Couldn't figure out how this promo code was generated")

        self.request.session["gift_giver_subscription"] = gift_giver_subscription.id

        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "code": self.kwargs.get("code", None),
            **super().get_context_data(**kwargs),
        }


class GiftMembershipSetupView(MemberSignupUserRegistrationMixin, FormView):
    template_name = "app/redeem_setup.html"
    form_class = StripeShippingForm
    success_url = reverse_lazy("member_signup_complete")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        if self.request.session.get("gift_giver_subscription", None) is None:
            redirect("redeem")
            return {}
        return super().get_context_data(**kwargs)

    def get_initial(self, *args, **kwargs):
        initial = {"name": self.request.user.get_full_name(), "country": "GB"}
        if self.request.user.stripe_customer is not None:
            shipping_data = self.request.user.stripe_customer.shipping
            if shipping_data is not None:
                initial.update(
                    {
                        key: value
                        for key, value in StripeShippingForm.stripe_data_to_initial(
                            shipping_data
                        ).items()
                        if value is not None
                    }
                )
        return initial

    def form_valid(self, form):
        if self.request.session.get("gift_giver_subscription", None) is None:
            return redirect("redeem")

        # Create subscription
        # try:
        self.finish_gift_redemption(self.request.session["gift_giver_subscription"])
        self.request.session["gift_giver_subscription"] = None
        # except Exception as error:
        #     print(error)
        #     self.request.session["gift_giver_subscription"] = None
        #     return redirect(reverse_lazy('redeem'))

        customer = stripe.Customer.modify(
            self.request.user.stripe_customer.id, shipping=form.to_stripe()
        )
        djstripe.models.Customer.sync_from_stripe_data(customer)

        return super().form_valid(form)

    def finish_gift_redemption(self, gift_giver_subscription_id) -> dict:
        if self.request.user.stripe_customer is not None:
            self.request.user.cleanup_membership_subscriptions()

        try:
            stripe_sub = stripe.Subscription.retrieve(gift_giver_subscription_id)
            gift_giver_subscription = (
                djstripe.models.Subscription.sync_from_stripe_data(stripe_sub)
            )
            create_gift(gift_giver_subscription, self.request.user)
        except djstripe.models.Subscription.DoesNotExist:
            raise ValueError(
                "Couldn't set up your gifted subscription. Please email info@leftbookclub.com and we'll get you started!"
            )

        return {}


class CancellationView(LoginRequiredTemplateView):
    template_name = "account/cancel.html"

    def post(self, request, *args, **kwargs):
        if self.request.method == "POST":
            if self.request.user.is_member:
                stripe.Subscription.delete(self.request.user.active_subscription.id)
                return HttpResponseRedirect(reverse("account_membership"))
        return super().dispatch(request, *args, **kwargs)


import stripe
from djstripe import webhooks

from app.utils.stripe import gift_recipient_subscription_from_code


@webhooks.handler("customer.subscription.deleted")
def gift_giver_subscription_was_cancelled(event, **kwargs):
    some_subscription = event.data.object
    if some_subscription.metadata.get("gift_mode", None) is not None:
        promo_code = some_subscription.metadata.get("promo_code", None)
        recipient_subscription = gift_recipient_subscription_from_code(promo_code)
        stripe.Subcription.delete(recipient_subscription.id)


class ShippingForProductView(TemplateView):
    template_name = "app/confirm_shipping.html"

    url_params = ["<price_id>/<product_id>/", "<price_id>/<product_id>/<country_id>/"]

    def get_context_data(
        self, price_id, product_id, country_id="GB", **kwargs
    ) -> Dict[str, Any]:
        """
        When a product has been selected, select shipping country.
        """
        from app.models.wagtail import MembershipPlanPage, MembershipPlanPrice

        context = super().get_context_data(**kwargs)
        product = LBCProduct.objects.get(id=product_id)
        price = MembershipPlanPrice.objects.get(
            id=price_id, plan__products__id=product_id
        )

        context.update(
            {
                "price": price,
                "product": product,
                "default_country_code": country_id,
                "country_selector_form": CountrySelectorForm(
                    initial={"country": country_id}
                ),
                "url_pattern": ShippingCostView.url_pattern,
            }
        )

        return context


class ShippingCostView(TemplateView):
    template_name = "app/frames/shipping_cost.html"
    url_pattern = "shippingcosts/<price_id>/<product_id>/<country_id>/"

    def get_context_data(self, price_id, product_id, country_id="GB", **kwargs):
        """
        Display shipping fee based on selected country
        """
        from app.models.wagtail import MembershipPlanPage, MembershipPlanPrice

        from .models import LBCProduct, ShippingZone

        context = super().get_context_data(**kwargs)
        price = MembershipPlanPrice.objects.get(id=price_id)
        product = LBCProduct.objects.get(id=product_id)
        zone = ShippingZone.get_for_country(country_id)
        context = {
            **context,
            "zone": zone,
            "price": price,
            "product": product,
            "shipping_zone": zone,
            "shipping_price": price.shipping_fee(zone),
            "final_price": price.price_including_shipping(zone),
            "url_pattern": self.url_pattern,
        }

        return context


class SubscriptionCheckoutView(TemplateView):
    """
    Create a checkout session with a line item of price_id
    """

    url_params = "<price_id>/<product_id>/"

    # TODO: should take an array of price_id, actually
    def get(
        self,
        request: HttpRequest,
        *args: Any,
        product_id=None,
        price_id=None,
        **kwargs: Any,
    ):
        from app.models.wagtail import MembershipPlanPrice

        country = request.GET.get("country", "GB")
        gift_mode = request.GET.get("gift_mode", None)
        product = LBCProduct.objects.get(id=product_id)
        price = MembershipPlanPrice.objects.get(
            id=price_id, plan__products__id=product_id
        )
        zone = ShippingZone.get_for_country(country)

        checkout_args = dict(
            mode="subscription",
            line_items=[
                {
                    "price_data": price.to_price_data(product),
                    "quantity": 1,
                },
                {
                    "price_data": price.to_shipping_price_data(zone),
                    "quantity": 1,
                },
            ],
            # By default, customer details aren't updated, but we want them to be.
            customer_update={
                "shipping": "auto",
                "address": "auto",
                "name": "auto",
            },
            metadata={},
        )
        callback_url_args = {}

        if gift_mode is not None and gift_mode is not False:
            callback_url_args["gift_mode"] = True
            checkout_args["metadata"]["gift_mode"] = True
        else:
            checkout_args["shipping_address_collection"] = {
                "allowed_countries": zone.country_codes
            }

        checkout_args["success_url"] = urllib.parse.urljoin(
            settings.BASE_URL,
            reverse_lazy("member_signup_complete")
            + "?session_id={CHECKOUT_SESSION_ID}&"
            + urlencode(callback_url_args),
        )
        checkout_args["cancel_url"] = urllib.parse.urljoin(
            settings.BASE_URL,
            "?" + urlencode(callback_url_args),
        )

        return CreateCheckoutSessionView.as_view(context=checkout_args)(request)
