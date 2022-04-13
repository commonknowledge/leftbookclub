from pipes import Template
from re import template

import djstripe
import stripe
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
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
        metadata = {
            f"{djstripe_settings.djstripe_settings.SUBSCRIBER_CUSTOMER_KEY}": user.id
        }

        session_args = dict(
            **self.context,
            metadata=metadata,
        )

        try:
            additional_args = {}
            # retreive the Stripe Customer.
            customer, is_new = user.get_or_create_customer()
            if customer is not None:
                additional_args["customer"] = customer.id
            elif user.email is not None:
                additional_args["customer_email"] = user.email

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
        session = stripe.checkout.Session.retrieve(self.request.GET.get("session_id"))
        customer_from_stripe = stripe.Customer.retrieve(session.customer)
        customer, is_new = djstripe.models.Customer._get_or_create_from_stripe_object(
            customer_from_stripe
        )

        # Relate the django user to this customer
        customer.subscriber = self.request.user
        customer.save()

        # Sync Stripe data to Django
        self.request.user.refresh_stripe_data()

        # Get parent Context
        context = super().get_context_data(**kwargs)

        return context


class ShippingCostView(TemplateView):
    template_name = "app/frames/shipping_cost.html"
    url_pattern = "shippingcosts/<str:product_id>/<str:country_id>/"

    def get_context_data(self, product_id=None, country_id=None, **kwargs):
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


class StripeCustomerPortalView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, **kwargs):
        return_url = self.request.build_absolute_uri(reverse("account_membership"))
        session = stripe.billing_portal.Session.create(
            customer=self.request.user.stripe_customer.id,
            return_url=return_url,
        )
        return session.url
