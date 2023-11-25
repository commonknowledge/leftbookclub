from typing import Any, Dict, List

import urllib.parse
from datetime import datetime

## v2
from enum import Enum
from importlib.metadata import metadata
from multiprocessing.sharedctypes import Value
from pipes import Template
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse

import djstripe.enums
import djstripe.models
import stripe
from dateutil.relativedelta import relativedelta
from django import forms
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponseRedirect
from django.http.response import Http404, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import include, path, re_path, reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import RedirectView, TemplateView, View
from django.views.generic.edit import FormView
from djmoney.money import Money
from djstripe import settings as djstripe_settings
from sentry_sdk import capture_exception, capture_message
from wagtail.models import Page

from app import analytics
from app.forms import (
    CountrySelectorForm,
    DonationForm,
    GiftCodeForm,
    SelectDeliveriesForm,
    SelectPaymentPlanForm,
    SelectSyllabusForm,
    StripeShippingForm,
    UpgradeForm,
)
from app.models import LBCProduct, User
from app.models.stripe import LBCSubscription, ShippingZone
from app.models.wagtail import BaseShopifyProductPage, MembershipPlanPrice
from app.utils.mailchimp import tag_user_in_mailchimp
from app.utils.shopify import create_shopify_order
from app.utils.stripe import (
    configure_gift_giver_subscription_and_code,
    create_donation_line_item,
    create_gift_recipient_subscription,
    gift_giver_subscription_from_code,
)


class SessionKey(Enum):
    delivery_plan_id = "v2signupflow_delivery_plan_id"
    syllabus_id = "v2signupflow_syllabus_id"
    country = "v2signupflow_country"
    payment_plan_id = "v2signupflow_payment_plan_id"
    donation_amount = "v2signupflow_donation_amount"


##


class MemberSignupUserRegistrationMixin(LoginRequiredMixin):
    login_url = reverse_lazy("account_signup")


class StripeCheckoutView(MemberSignupUserRegistrationMixin, RedirectView):
    context = {}

    def get_redirect_url(self, **kwargs):
        """
        Creates and returns a Stripe Checkout Session.
        - Pass context arg `next` to redirect after StripeCheckoutSuccessView.
        """
        # get the id of the Model instance of djstripe_settings.djstripe_settings.get_subscriber_model()
        # here we have assumed it is the Django User model. It could be a Team, Company model too.
        # note that it needs to have an email field.
        user = self.request.user

        # example of how to insert the SUBSCRIBER_CUSTOMER_KEY: id in the metadata
        # to add customer.subscriber to the newly created/updated customer.
        session_args = self.context.get("checkout_args", {})
        session_args["metadata"] = session_args.get("metadata", {})
        session_args["metadata"][
            djstripe_settings.djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
        ] = user.id
        session_args["metadata"]["gdpr_email_consent"] = user.gdpr_email_consent

        # redirect the checkout success to StripeCheckoutSuccessView,
        # which will then forward to any explicitly defined `success_url` that was passed to this view
        session_args["success_url"] = urllib.parse.urljoin(
            settings.BASE_URL,
            reverse_lazy("stripe_checkout_success")
            + "?session_id={CHECKOUT_SESSION_ID}"
            + "&next="
            + self.context.get("next", reverse_lazy("account_membership")),
        )
        session_args["cancel_url"] = urllib.parse.urljoin(
            base=settings.BASE_URL, url=self.context.get("cancel_url", "/")
        )

        try:
            if user.primary_email is not None:
                session_args["customer_email"] = user.primary_email

            # retreive the Stripe Customer.
            customer, is_new = user.get_or_create_customer()
            if customer is not None:
                session_args.pop("customer_email")
                session_args["customer"] = customer.id
        except djstripe.models.Customer.DoesNotExist:
            pass

        # ! Note that Stripe will always create a new Customer Object if customer id not provided
        # ! even if customer_email is provided!
        session = stripe.checkout.Session.create(**session_args)

        analytics.visit_stripe_checkout(user)

        return session.url


class StripeCheckoutSuccessView(LoginRequiredMixin, TemplateView):
    template_name = "stripe/checkout_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_id = self.request.GET.get("session_id", None)

        # v2
        for key in SessionKey:
            self.request.session[key.value] = None
        #

        # Construct `next` URL to redirect to
        # including session_id, so that context can be built up in the view
        next_url = self.request.GET.get("next", "/")
        next_parsed = urlparse(next_url)
        next_params = dict(parse_qsl(next_parsed.query))
        success_params = {"session_id": session_id}
        merged_params = urlencode({**next_params, **success_params})
        next_parsed = next_parsed._replace(query=merged_params)
        context["next"] = next_parsed.geturl()

        #
        gift_mode = False
        session = None
        customer = None
        subscription = None

        if session_id is not None:
            session = stripe.checkout.Session.retrieve(session_id)
            gift_mode = session.metadata.get("gift_mode", None) is not None
            customer_from_stripe = stripe.Customer.retrieve(session.customer)
            (
                customer,
                is_new,
            ) = djstripe.models.Customer._get_or_create_from_stripe_object(
                customer_from_stripe
            )

            if session.payment_intent is not None:
                payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
                # Context for fbq tracking
                context["payment_intent"] = payment_intent
                context["value"] = payment_intent.amount / 100
                context["currency"] = payment_intent.currency

            elif session.subscription is not None:
                subscription = stripe.Subscription.retrieve(
                    session.subscription, expand=["latest_invoice"]
                )

                if (
                    subscription is not None
                    and subscription.metadata.get("processed", None) is None
                ):
                    # Context for fbq tracking
                    context["subscription"] = subscription
                    context["value"] = subscription.latest_invoice.amount_due / 100
                    context["currency"] = subscription.latest_invoice.currency

                    if gift_mode:
                        """
                        Resolve gift purchase by creating a promo code and relating it to the gift buyer's subscription,
                        for future reference.
                        """
                        self.finish_gift_purchase(session, subscription, customer)
                        analytics.buy_gift(self.request.user)
                        tag_user_in_mailchimp(
                            self.request.user, tags_to_enable=["GIFT_GIVER"]
                        )
                        prod_id = session.metadata.get("primary_product")
                        prod = djstripe.models.Product.objects.get(id=prod_id)
                        create_shopify_order(
                            self.request.user,
                            line_items=[
                                {
                                    "title": f"Gift Card Purchase - {prod.name}",
                                    "quantity": 1,
                                    "price": 0,
                                }
                            ],
                            tags=["Gift Card Purchase"],
                        )
                    else:
                        """
                        Resolve a normal membership purchase
                        """
                        self.finish_self_purchase(session, subscription, customer)
                        analytics.buy_membership(self.request.user)
                        tag_user_in_mailchimp(
                            self.request.user,
                            tags_to_enable=["MEMBER"],
                            tags_to_disable=["CANCELLED"],
                        )
                        prod_id = session.metadata.get("primary_product", None)
                        prod = djstripe.models.Product.objects.get(id=prod_id)
                        create_shopify_order(
                            self.request.user,
                            line_items=[
                                {
                                    "title": f"Membership Subscription Purchase — {prod.name}",
                                    "quantity": 1,
                                    "price": 0,
                                }
                            ],
                            tags=["Membership Subscription Purchase"],
                        )

                    analytics.signup(self.request.user)

                    stripe.Subscription.modify(
                        subscription.id, metadata={"processed": True}
                    )

        return context

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
            (
                promo_code,
                gift_giver_subscription,
            ) = configure_gift_giver_subscription_and_code(
                session.subscription, self.request.user.id
            )
            page_context["promo_code"] = promo_code
            page_context["gift_giver_subscription"] = gift_giver_subscription

            # Send them this promo code via email
            redeem_url = self.request.build_absolute_uri(
                reverse("redeem", kwargs={"code": promo_code.code})
            )
            try:
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
            except Exception as e:
                capture_exception(e)
                pass

        return page_context


class CompletedMembershipPurchaseView(MemberSignupUserRegistrationMixin, TemplateView):
    template_name = "app/completed_membership_purchase.html"


class CompletedGiftPurchaseView(MemberSignupUserRegistrationMixin, TemplateView):
    template_name = "app/completed_gift_purchase.html"

    def get_context_data(self, *args, **kwargs):
        page_context = super().get_context_data(**kwargs)
        session_id = self.request.GET.get("session_id")
        page_context["session"] = stripe.checkout.Session.retrieve(session_id)
        page_context["gift_giver_subscription"] = stripe.Subscription.retrieve(
            page_context["session"].subscription
        )
        page_context["promo_code"] = stripe.PromotionCode.retrieve(
            page_context["gift_giver_subscription"]
            .get("metadata", {})
            .get("promo_code")
        )
        return page_context


class CompletedGiftRedemptionView(MemberSignupUserRegistrationMixin, TemplateView):
    template_name = "app/completed_gift_redemption.html"


class LoginRequiredTemplateView(LoginRequiredMixin, TemplateView):
    pass


class StripeCustomerPortalView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, **kwargs):
        return_url = self.request.build_absolute_uri(reverse("account_membership"))
        session = stripe.billing_portal.Session.create(
            customer=self.request.user.stripe_customer.id,
            return_url=return_url,
        )
        analytics.visit_stripe_customerportal(self.request.user)
        return session.url


class CartOptionsView(TemplateView):
    template_name = "app/frames/cart_options.html"
    url_pattern = "anonymous/cartoptions/<product_id>/"

    def get_context_data(self, product_id=None, **kwargs):
        from .models import BookPage

        context = super().get_context_data(**kwargs)
        product = BaseShopifyProductPage.get_specific_product_by_shopify_id(product_id)
        context = {
            **context,
            "product": product.nocache_shopify_product,
            "disabled": self.request.GET.get("disabled") == "True",
        }

        return context


class GiftCodeRedeemView(FormView):
    template_name = "app/redeem.html"
    form_class = GiftCodeForm
    success_url = reverse_lazy("redeem_setup")

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
    success_url = reverse_lazy("completed_gift_redemption")

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

        # Stop showing a "finish redemption" notice
        self.request.session["gift_giver_subscription"] = None
        # except Exception as error:
        #     print(error)
        #     self.request.session["gift_giver_subscription"] = None
        #     return redirect(reverse_lazy('redeem'))

        customer = stripe.Customer.modify(
            self.request.user.stripe_customer.id, shipping=form.to_stripe()
        )
        djstripe.models.Customer.sync_from_stripe_data(customer)

        analytics.redeem(self.request.user)
        tag_user_in_mailchimp(
            self.request.user,
            tags_to_enable=["MEMBER", "GIFT_RECIPIENT"],
            tags_to_disable=["CANCELLED"],
        )
        create_shopify_order(
            self.request.user,
            line_items=[
                {
                    "title": f"Gift Card Redeemed — {self.request.user.primary_product.name}",
                    "quantity": 1,
                    "price": 0,
                }
            ],
            tags=["Membership Subscription Purchase", "Gift Card Redeemed"],
        )

        return super().form_valid(form)

    def finish_gift_redemption(self, gift_giver_subscription_id) -> dict:
        try:
            stripe_sub = stripe.Subscription.retrieve(gift_giver_subscription_id)
            gift_giver_subscription = (
                djstripe.models.Subscription.sync_from_stripe_data(stripe_sub)
            )
            gift_recipient_subscription = create_gift_recipient_subscription(
                gift_giver_subscription, self.request.user
            )
            if self.request.user.stripe_customer is not None:
                self.request.user.cleanup_membership_subscriptions(
                    keep=[gift_recipient_subscription.id]
                )
        except djstripe.models.Subscription.DoesNotExist as e:
            capture_exception(e)
            raise ValueError(
                "Couldn't set up your gifted subscription. Please email info@leftbookclub.com and we'll get you started!"
            )

        return {}


class CancellationView(LoginRequiredTemplateView):
    template_name = "account/cancel.html"

    def get_context_data(self, subscription_id=None, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if (
            subscription_id is not None
            and self.request.user.stripe_customer is not None
        ):
            try:
                context["subscription"] = LBCSubscription.objects.filter(
                    customer=self.request.user.stripe_customer, id=subscription_id
                ).first()
                return context
            except djstripe.models.Subscription.DoesNotExist:
                raise Http404
        else:
            context["subscription"] = self.request.user.active_subscription
            return context

    def post(self, request, *args, subscription_id=None, **kwargs):
        if request.method == "POST":
            if subscription_id is None:
                subscription_id = request.user.active_subscription.id
            if request.user.stripe_customer is not None:
                sub = LBCSubscription.objects.filter(
                    customer=request.user.stripe_customer, id=subscription_id
                ).first()
                if sub is not None:
                    analytics.cancel_membership(request.user.stripe_customer.subscriber)
                    stripe.Subscription.modify(
                        subscription_id, cancel_at_period_end=True
                    )
                    if sub.gift_giver_subscription is not None:
                        stripe.Subscription.modify(
                            sub.gift_giver_subscription.id, cancel_at_period_end=True
                        )
                    if sub.gift_recipient_subscription is not None:
                        stripe.Subscription.modify(
                            sub.gift_recipient_subscription.id,
                            cancel_at_period_end=True,
                        )
                    return HttpResponseRedirect(reverse("account_membership"))
        raise Http404


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
        price = MembershipPlanPrice.objects.get(id=price_id, products__id=product_id)

        context.update(
            {
                "price": price,
                "product": product,
                "upsell": price.upsell_data(product_id, country_id),
                "default_country_code": country_id,
                "country_selector_form": CountrySelectorForm(
                    initial={"country": country_id}
                ),
                "url_pattern": ShippingCostView.url_pattern,
                "current_book": product.current_book,
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

    @classmethod
    def create_checkout_context(
        cls,
        product: LBCProduct,
        price: MembershipPlanPrice,
        zone: ShippingZone,
        gift_mode: bool = False,
    ) -> dict:
        if product is None:
            raise ValueError("product required to create checkout")
        if price is None:
            raise ValueError("price required to create checkout")
        if zone is None:
            raise ValueError("zone required to create checkout")

        checkout_args = dict(
            mode="subscription",
            allow_promotion_codes=True,
            line_items=price.to_checkout_line_items(product=product, zone=zone),
            # By default, customer details aren't updated, but we want them to be.
            customer_update={
                "shipping": "auto",
                "address": "auto",
                "name": "auto",
            },
            shipping_address_collection={"allowed_countries": zone.country_codes},
            metadata={"primary_product": product.id},
        )

        next = "/"
        if gift_mode:
            checkout_args["metadata"]["gift_mode"] = True
            next = reverse_lazy("completed_gift_purchase")
        else:
            next = reverse_lazy("completed_membership_purchase")

        return {
            "checkout_args": checkout_args,
            "next": next,
            "cancel_url": price.plan.url,
            "breadcrumbs": {
                "price": price,
                "product": product,
                "zone": zone,
                "gift_mode": gift_mode,
            },
        }

    def get(
        self,
        request: HttpRequest,
        *args: Any,
        product_id=None,
        price_id=None,
        **kwargs: Any,
    ):
        country = request.GET.get("country", "GB")
        zone = ShippingZone.get_for_country(country)
        gift_mode = request.GET.get("gift_mode", None)
        gift_mode = gift_mode is not None and gift_mode is not False
        product = LBCProduct.objects.get(id=product_id)
        price = MembershipPlanPrice.objects.get(id=price_id, products__id=product_id)

        checkout_context = SubscriptionCheckoutView.create_checkout_context(
            product=product, price=price, zone=zone, gift_mode=gift_mode
        )

        return StripeCheckoutView.as_view(context=checkout_context)(request)


from django.shortcuts import get_object_or_404


class ProductRedirectView(RedirectView):
    def get_redirect_url(self, id, **kwargs):
        product = BaseShopifyProductPage.get_specific_product_by_shopify_id(id)

        if product is None:
            raise Http404

        return product.url


from django_dbq.models import Job


@method_decorator(csrf_exempt, name="dispatch")
class SyncShopifyWebhookEndpoint(View):
    def put(self, request, *args, **kwargs):
        """
        Trigger the sync_shopify_products command.
        """
        self.create_job()
        return HttpResponse(status=200)

    def post(self, request, *args, **kwargs):
        """
        Trigger the sync_shopify_products command.
        """
        self.create_job()
        return HttpResponse(status=200)

    def get(self, request, *args, **kwargs):
        """
        Trigger the sync_shopify_products command.
        """
        self.create_job()
        return HttpResponse(status=200)

    def create_job(self):
        already_queued = Job.objects.filter(
            name="sync_shopify_products", state__in=[Job.STATES.READY, Job.STATES.NEW]
        ).exists()
        if already_queued:
            return
        Job.objects.create(name="sync_shopify_products")


class WagtailStreamfieldBlockTurboFrame(TemplateView):
    def get_context_data(self, page_id=None, field_name=None, block_id=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_id": page_id,
                "field_name": field_name,
                "block_id": block_id,
                **WagtailStreamfieldBlockTurboFrame.get_block_context(
                    page_id, field_name, block_id
                ),
            }
        )
        return context

    @classmethod
    def get_block_context(cls, page_id, field_name, block_id):
        context = {}
        page = Page.objects.get(id=page_id)
        for block in getattr(page.specific, field_name):
            if block.id == block_id:
                context["value"] = block.value
                context.update(block.block.get_context(block.value))
                break
        return context


from django.contrib.auth.mixins import UserPassesTestMixin


class SuperUserCheck(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser


class RefreshDataView(SuperUserCheck, LoginRequiredMixin, TemplateView):
    template_name = "app/refreshed.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        from django.core import management

        from app.models import BookPage, CircleEvent, MerchandisePage

        CircleEvent.sync()
        # BookPage.sync_shopify_products_to_pages()
        # MerchandisePage.sync_shopify_products_to_pages()
        return super().get_context_data(**kwargs)


class UpgradeView(LoginRequiredMixin, FormView):
    form_class = UpgradeForm
    template_name = "app/upgrade.html"
    success_url = reverse_lazy("upgrade-success")

    def form_valid(self, form: UpgradeForm):
        form.update_subscription()
        return super().form_valid(form)

    def get_initial(self):
        if isinstance(self.request.user, User):
            initial = super().get_initial()
            initial["fee_option"] = "STATUS_QUO"
            initial["user_id"] = self.request.user.pk
            return initial

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if isinstance(self.request.user, User):
            context.update(
                {"options": UpgradeForm.get_options_for_user(self.request.user)}
            )
        return context


class UpgradeSuccessDonationTrailerView(LoginRequiredMixin, FormView):
    form_class = DonationForm
    template_name = "app/upgrade_success.html"
    success_url = reverse_lazy("donation-success")

    def get_initial(self):
        if isinstance(self.request.user, User):
            initial = super().get_initial()
            initial["user_id"] = self.request.user.pk
            initial["donation_amount"] = 2
            return initial

    def form_valid(self, form: DonationForm):
        form.update_subscription()
        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["donation_amount_options"] = [1, 2, 3]
        return context


class DonationView(UpgradeSuccessDonationTrailerView):
    form_class = DonationForm
    template_name = "app/donate.html"
    success_url = reverse_lazy("donation-success")

    def get_initial(self):
        if isinstance(self.request.user, User):
            initial = super().get_initial()
            initial["user_id"] = self.request.user.pk
            if self.request.user.active_subscription.donation_si is not None:
                initial["donation_amount"] = float(
                    self.request.user.active_subscription.donation_si.plan.amount
                )
            return initial


from .forms import BatchUpdateSubscriptionsForm


class BatchUpdateSubscriptionsView(SuperUserCheck, LoginRequiredMixin, FormView):
    form_class = BatchUpdateSubscriptionsForm
    template_name = "app/batch_update_subscriptions.html"

    def form_valid(self, form: BatchUpdateSubscriptionsForm):
        form.process_request()
        self.success_url = reverse(
            "batch_update_subscriptions_batch_status",
            kwargs={"batch_id": form.cleaned_data["batch_id"]},
        )
        print(self.success_url)
        return super().form_valid(form)


class BatchUpdateSubscriptionsStatusView(
    SuperUserCheck, LoginRequiredMixin, TemplateView
):
    template_name = "app/batch_update_subscriptions_status.html"

    def get_context_data(self, batch_id=None, **kwargs):
        context = super().get_context_data(**kwargs)
        retry_job_id = self.request.GET.get("retry_job_id", None)
        if retry_job_id is not None:
            self.retry_job(retry_job_id)
        context["batch_id"] = batch_id
        context["jobs"] = Job.objects.filter(workspace__batch_id=batch_id).order_by(
            "-created"
        )
        return context

    def retry_job(self, retry_job_id):
        job = Job.objects.filter(id=retry_job_id, workspace__retry_job_id=None).first()
        if job is None:
            return
        new_job = Job.objects.create(
            name=job.name,
            workspace={**job.workspace, "original_job_id": str(retry_job_id)},
        )
        job.workspace["retry_job_id"] = str(new_job.id)
        job.save()


"""
### V2 flow 

CreateMembershipView (alias) ->

SelectDeliveriesView
- List of MembershipPlanPage.filter(display_in_quiz_flow=True)

SelectSyllabusView
- TEST: (if only one syllabus, send straight on to shipping)

SelectShippingCountryView
- Cannibalise ShippingForProductView to just get the country

SelectBillingPlanView
- Requires delivery plan + shipping country

SelectDonationView

StripeCheckoutView
- Requires payment plan + shipping country + donation config

WelcomeView
"""


class OneAtATimeFormViewStoredToSession(FormView):
    session_key: SessionKey
    default_value = None
    require: List[SessionKey] = []
    require_redirect = "signup"

    def dispatch(self, request, *args, **kwargs):
        for key in self.require:
            if not self.request.session.get(key.value, False):
                return redirect(self.require_redirect)
        return super().dispatch(request, *args, **kwargs)

    def initial_form_value(self):
        saved_value = self.request.session.get(self.session_key.value, None)
        if saved_value is not None:
            return saved_value
        else:
            return self.default_value

    def get_initial(self):
        initial = super().get_initial()
        initial[self.session_key.name] = self.initial_form_value()
        return initial

    def serialize_value(self, value):
        return value

    def form_valid(self, form: SelectPaymentPlanForm):
        self.request.session[self.session_key.value] = self.serialize_value(
            form.cleaned_data[self.session_key.name]
        )
        return super().form_valid(form)

    @cached_property
    def plan(self):
        plan_id = self.request.session.get(SessionKey.delivery_plan_id.value, False)
        if plan_id:
            from app.models.wagtail import MembershipPlanPage

            return MembershipPlanPage.objects.get(id=plan_id)

    @cached_property
    def syllabus(self):
        syllabus_id = self.request.session.get(SessionKey.syllabus_id.value, False)
        if syllabus_id:
            from app.models.wagtail import SyllabusPage

            return SyllabusPage.objects.get(id=syllabus_id)

    @cached_property
    def price(self):
        price_id = self.request.session.get(SessionKey.payment_plan_id.value, False)
        if price_id:
            from app.models.wagtail import MembershipPlanPrice

            return MembershipPlanPrice.objects.get(id=price_id)

    @cached_property
    def country(self):
        country_code = self.request.session.get(SessionKey.country.value, False)
        return country_code

    @cached_property
    def zone(self):
        if self.country is None:
            return ShippingZone.default_zone
        return ShippingZone.get_for_country(iso_a2=self.country)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["plan"] = self.plan
        context["zone"] = self.zone
        context["syllabus"] = self.syllabus
        context["price"] = self.price
        context["country"] = self.country
        context["field_name"] = self.session_key.name
        context["field_value"] = self.initial_form_value()
        return context


class SelectDeliveriesView(OneAtATimeFormViewStoredToSession):
    template_name = "app/signup/select_deliveries.html"
    form_class = SelectDeliveriesForm
    success_url = reverse_lazy("signup_syllabus")
    session_key = SessionKey.delivery_plan_id

    def get_context_data(self, **kwargs):
        from app.models.wagtail import MembershipPlanPage

        context = super().get_context_data(**kwargs)
        context["delivery_options"] = MembershipPlanPage.objects.filter(
            display_in_quiz_flow=True
        )
        context["steps"] = [
            {"title": "Reading speed", "current": True},
            {"title": "Syllabus", "current": False},
            {"title": "Shipping", "current": False},
            {"title": "Billing", "current": False},
            {"title": "Checkout", "current": False},
        ]
        return context


class CreateMembershipView(SelectDeliveriesView):
    pass


class SelectSyllabusView(OneAtATimeFormViewStoredToSession):
    template_name = "app/signup/select_syllabus.html"
    form_class = SelectSyllabusForm
    success_url = reverse_lazy("signup_shipping")
    session_key = SessionKey.syllabus_id
    require = [SessionKey.delivery_plan_id]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["syllabus_options"] = context.get("plan").syllabi.all()
        context["steps"] = [
            {
                "title": "Reading speed",
                "current": False,
                "href": reverse_lazy("signup_deliveries"),
            },
            {"title": "Syllabus", "current": True},
            {"title": "Shipping", "current": False},
            {"title": "Billing", "current": False},
            {"title": "Checkout", "current": False},
        ]
        return context


class SelectShippingCountryView(OneAtATimeFormViewStoredToSession):
    template_name = "app/signup/select_shipping.html"
    form_class = CountrySelectorForm
    success_url = reverse_lazy("signup_billing")
    session_key = SessionKey.country
    default_value = "GB"
    require = [
        SessionKey.delivery_plan_id,
        SessionKey.syllabus_id,
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["steps"] = [
            {
                "title": "Reading speed",
                "current": False,
                "href": reverse_lazy("signup_deliveries"),
            },
            {
                "title": "Syllabus",
                "current": False,
                "href": reverse_lazy("signup_syllabus"),
            },
            {"title": "Shipping", "current": True},
            {"title": "Billing", "current": False},
            {"title": "Checkout", "current": False},
        ]
        return context


class SelectBillingPlanView(OneAtATimeFormViewStoredToSession):
    template_name = "app/signup/select_billing.html"
    form_class = SelectPaymentPlanForm
    success_url = reverse_lazy("signup_donation")
    session_key = SessionKey.payment_plan_id
    require = [
        SessionKey.delivery_plan_id,
        SessionKey.syllabus_id,
        SessionKey.country,
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payment_options"] = [
            {
                "price": price,
                "shipping_price": price.shipping_fee(self.zone),
                "price_with_shipping": price.price_string_including_shipping(self.zone),
                "equivalent_monthly_price_including_shipping": price.equivalent_monthly_price_string_including_shipping(
                    self.zone
                ),
                "equivalent_monthly_shipping_price": self.zone.rate,
            }
            for price in context.get("plan").prices.all()
        ]
        context["steps"] = [
            {
                "title": "Reading speed",
                "current": False,
                "href": reverse_lazy("signup_deliveries"),
            },
            {
                "title": "Syllabus",
                "current": False,
                "href": reverse_lazy("signup_syllabus"),
            },
            {
                "title": "Shipping",
                "current": False,
                "href": reverse_lazy("signup_shipping"),
            },
            {"title": "Billing", "current": True},
            {"title": "Checkout", "current": False},
        ]
        return context


class SelectDonationView(OneAtATimeFormViewStoredToSession):
    form_class = DonationForm
    template_name = "app/signup/select_donation.html"
    success_url = reverse_lazy("v2_stripe_checkout")
    session_key = SessionKey.donation_amount
    default_value = 3
    require = [
        SessionKey.delivery_plan_id,
        SessionKey.syllabus_id,
        SessionKey.payment_plan_id,
        SessionKey.country,
    ]

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["donation_amount_options"] = [1, 3, 5]
        context["steps"] = [
            {
                "title": "Reading speed",
                "current": False,
                "href": reverse_lazy("signup_deliveries"),
            },
            {
                "title": "Syllabus",
                "current": False,
                "href": reverse_lazy("signup_syllabus"),
            },
            {
                "title": "Shipping",
                "current": False,
                "href": reverse_lazy("signup_shipping"),
            },
            {
                "title": "Billing",
                "current": False,
                "href": reverse_lazy("signup_billing"),
            },
            {"title": "Checkout", "current": False},
        ]
        return context

    def serialize_value(self, value):
        return int(value)


class V2SubscriptionCheckoutView(TemplateView):
    @classmethod
    def create_checkout_context(
        cls,
        product: LBCProduct,
        price: MembershipPlanPrice,
        zone: ShippingZone,
        gift_mode: bool = False,
        donation_amount: int = 0,
    ) -> dict:
        if product is None:
            raise ValueError("product required to create checkout")
        if price is None:
            raise ValueError("price required to create checkout")
        if zone is None:
            raise ValueError("zone required to create checkout")

        checkout_args = dict(
            mode="subscription",
            allow_promotion_codes=True,
            line_items=price.to_checkout_line_items(product=product, zone=zone),
            # By default, customer details aren't updated, but we want them to be.
            customer_update={
                "shipping": "auto",
                "address": "auto",
                "name": "auto",
            },
            shipping_address_collection={"allowed_countries": zone.country_codes},
            metadata={"primary_product": product.id},
        )

        if donation_amount > 0:
            checkout_args["line_items"].append(
                create_donation_line_item(
                    amount=donation_amount,
                    interval=price.interval,
                    currency=price.price.currency,
                    interval_count=price.interval_count,
                )
            )

        next = "/"
        if gift_mode:
            checkout_args["metadata"]["gift_mode"] = True
            next = reverse_lazy("completed_gift_purchase")
        else:
            next = reverse_lazy("completed_membership_purchase")

        return {
            "checkout_args": checkout_args,
            "next": next,
            "cancel_url": price.plan.url,
            "breadcrumbs": {
                "price": price,
                "product": product,
                "zone": zone,
                "gift_mode": gift_mode,
            },
        }

    def get(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ):
        from app.models.wagtail import SyllabusPage

        country = request.session.get(SessionKey.country.value, "GB")
        zone = ShippingZone.get_for_country(country)
        # TODO:
        # gift_mode = request.GET.get("gift_mode", None)
        # gift_mode = gift_mode is not None and gift_mode is not False
        gift_mode = False
        syllabus_id = request.session.get(SessionKey.syllabus_id.value)
        syllabus = SyllabusPage.objects.get(id=syllabus_id)
        product = syllabus.stripe_product
        price_id = request.session.get(SessionKey.payment_plan_id.value)
        price = MembershipPlanPrice.objects.get(id=price_id)
        donation_amount = request.session.get(SessionKey.donation_amount.value, 0)

        checkout_context = V2SubscriptionCheckoutView.create_checkout_context(
            product=product,
            price=price,
            zone=zone,
            gift_mode=gift_mode,
            donation_amount=donation_amount,
        )

        return StripeCheckoutView.as_view(context=checkout_context)(request)
