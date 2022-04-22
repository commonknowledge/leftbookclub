from typing import Any, Dict

from datetime import datetime
from multiprocessing.sharedctypes import Value

import djstripe.models
import stripe
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.edit import FormView
from djstripe import settings as djstripe_settings

from app.forms import GiftCodeForm
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


class CheckoutSessionCompleteView(MemberSignupUserRegistrationMixin, TemplateView):
    template_name = "app/welcome.html"

    def get_context_data(self, *args, **kwargs):
        # Get parent Context
        page_context = super().get_context_data(**kwargs)

        # Get checkout data
        session = stripe.checkout.Session.retrieve(self.request.GET.get("session_id"))
        customer_from_stripe = stripe.Customer.retrieve(session.customer)
        customer, is_new = djstripe.models.Customer._get_or_create_from_stripe_object(
            customer_from_stripe
        )
        subscription = stripe.Subscription.retrieve(session.subscription)
        gift_mode = session.metadata.get("gift_mode")

        if gift_mode is not None:
            page_context["gift_mode"] = True
            try:
                promo_code_id = subscription.metadata.get("promo_code", None)
                if promo_code_id is not None:
                    # Refreshed the page -- don't let them generate a new coupon each time they do that!
                    promo_code = stripe.PromotionCode.retrieve(promo_code_id)
                    page_context["promo_code"] = promo_code.code
                else:
                    # First time
                    subscription = stripe.Subscription.modify(
                        session.subscription,
                        metadata={"gift_mode": True},
                        cancel_at=(datetime.now() - relativedelta(days=1))
                        + relativedelta(months=settings.GIFT_MONTHS),
                    )
                    # 2. Generate coupon
                    product_id = subscription.get("items").data[0].price.product
                    coupon = stripe.Coupon.create(
                        applies_to={"products": [product_id]},
                        percent_off=100,
                        duration="repeating",
                        duration_in_months=settings.GIFT_MONTHS,
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

                    subscription = stripe.Subscription.modify(
                        session.subscription,
                        metadata={"promo_code": promo_code.id},
                    )

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
            except:
                page_context["error"] = True
        else:
            # Relate the django user to this customer
            customer.subscriber = self.request.user
            customer.save()

            # Delete old subscriptions
            for sub in self.request.user.stripe_customer.subscriptions.all():
                if (
                    sub.metadata.get("gift_mode", None) is None
                    and sub.id != subscription.id
                ):
                    try:
                        stripe.Subscription.delete(sub.id)
                    except:
                        pass

        subscription = djstripe.models.Subscription.sync_from_stripe_data(subscription)
        page_context["subscription"] = subscription

        # Sync Stripe data to Django
        self.request.user.refresh_stripe_data()

        return page_context


class ShippingCostView(TemplateView):
    template_name = "app/frames/shipping_cost.html"
    url_pattern = "shippingcosts/<str:product_id>/<str:country_id>/"

    def get_context_data(self, product_id=None, country_id=None, **kwargs):
        from .models import LBCProduct, ShippingZone

        context = super().get_context_data(**kwargs)
        if product_id is None or country_id is None:
            return context
        product = LBCProduct.objects.get(id=product_id)
        basic_price = product.basic_price
        shipping_price = product.get_prices_for_country(
            iso_a2=country_id,
            recurring__interval=basic_price.recurring["interval"],
            recurring__interval_count=basic_price.recurring["interval_count"],
        ).first()
        if basic_price is None or shipping_price is None:
            return context
        zone = ShippingZone.get_for_country(country_id)
        context = {
            **context,
            "zone": zone,
            "product": product,
            "shipping_fee": shipping_price.unit_amount - basic_price.unit_amount,
            "final_price": shipping_price,
            "url_pattern": self.url_pattern,
        }

        return context


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
    url_pattern = "cartoptions/<str:product_id>/"

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
    success_url = reverse_lazy("redeem_success")

    def form_valid(self, form):
        gift_giver_subscription = gift_giver_subscription_from_code(
            form.cleaned_data["code"]
        )
        if gift_giver_subscription is None:
            raise ValueError("Couldn't figure out how this promo code was generated")

        if self.request.user.stripe_customer is not None:
            # Cancel old subscriptions
            subscriptions = stripe.Subscription.list(
                customer=self.request.user.stripe_customer.id,
                status="active",
                limit=100,
            )
            for sub in subscriptions.data:
                if sub.metadata.get("gift_mode", None) is None:
                    stripe.Subscription.delete(sub)

        create_gift(gift_giver_subscription, self.request.user)
        return super().form_valid(form)

    def get_initial(self, *args, **kwargs):
        code = self.kwargs.get("code", None)
        if code is not None:
            return {"code": code}
        else:
            return super().get_initial()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "code": self.kwargs.get("code", None),
            **super().get_context_data(**kwargs),
        }


class GiftCodeRedeemSuccessView(LoginRequiredTemplateView):
    template_name = "app/welcome.html"


class CancellationView(LoginRequiredTemplateView):
    template_name = "account/cancel.html"

    def post(self, request, *args, **kwargs):
        if self.request.method == "POST":
            if self.request.user.is_member:
                stripe.Subscription.delete(self.request.user.active_subscription.id)
                return HttpResponseRedirect(reverse("account_membership"))
        return super().dispatch(request, *args, **kwargs)
