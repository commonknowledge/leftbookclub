from datetime import datetime

import djstripe.models
import stripe
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic.base import RedirectView, TemplateView
from djstripe import settings as djstripe_settings

from app.models import LBCProduct
from app.models.stripe import ShippingZone


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
    template_name = "app/post_purchase_success.html"

    def get_context_data(self, *args, **kwargs):
        # Get parent Context
        page_context = super().get_context_data(**kwargs)

        # Get checkout data
        session = stripe.checkout.Session.retrieve(self.request.GET.get("session_id"))
        customer_from_stripe = stripe.Customer.retrieve(session.customer)
        customer, is_new = djstripe.models.Customer._get_or_create_from_stripe_object(
            customer_from_stripe
        )
        gift_mode = session.metadata.get("gift_mode")

        if gift_mode is not None:
            # 1. Set cancel_at on subscription + apply metadata
            subscription = stripe.Subscription.retrieve(session.subscription)

            promo_code_id = subscription.metadata.get("promo_code_id", None)
            if promo_code_id is not None:
                # Refreshed the page -- don't let them generate a new coupon each time they do that!
                promo_code = stripe.PromotionCode.retrieve(promo_code_id)
            else:
                # First time
                subscription = stripe.Subscription.modify(
                    session.subscription,
                    metadata={"gift_mode": True},
                    cancel_at=datetime.now()
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
                        "related_gift_subscription": session.subscription,
                        "related_django_user": self.request.user.id,
                    },
                )

                subscription = stripe.Subscription.modify(
                    session.subscription,
                    metadata={"promo_code_id": promo_code.id},
                )

                # Send them this promo code via email
                send_mail(
                    "Your Left Book Club Gift Code",
                    f"Your gift code is {promo_code.code}. It can be redeemed at https://leftbookclub.com/redeem?code={promo_code.code}",
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
            page_context["gift_mode"] = True
            page_context["promo_code"] = promo_code.code
        else:
            # Relate the django user to this customer
            customer.subscriber = self.request.user
            customer.save()

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
