import urllib.parse

import stripe
from django.conf import settings
from django.shortcuts import redirect
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page

from .stripe import LBCProduct


class HomePage(RoutablePageMixin, Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body", classname="full"),
    ]

    @route(r"^$")  # will override the default Page serving mechanism
    def pick_product(self, request):
        """
        Provide a list of products to the template, to start the membership signup flow
        """

        products = LBCProduct.get_active_plans()

        return self.render(
            request,
            context_overrides={
                "products": products,
            },
            template="app/pick_product.html",
        )

    @route(r"^product/(?P<product_id>.+)/$")
    def pick_price_for_product(self, request, product_id):
        """
        When a product has been selected, present the regular/solidarity options.
        """

        # try:
        product = LBCProduct.objects.get(id=product_id)

        return self.render(
            request,
            context_overrides={"product": product},
            template="app/pick_price_for_product.html",
        )
        # except:
        #     if settings.DEBUG is False:
        #         return redirect(self.get_full_url(request) + self.reverse_subpage("subscription_error"))

    @route(r"^checkout/(?P<price_id>.+)/$")
    def checkout(self, request, price_id):
        """
        Create a checkout session with a line item of price_id
        """

        # try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            shipping_address_collection={"allowed_countries": ["GB"]},
            success_url=urllib.parse.urljoin(
                self.get_full_url(request), "complete?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=urllib.parse.urljoin(self.get_full_url(request), "error"),
        )

        response = redirect(session.url)
        return response
        # except:
        #     if settings.DEBUG is False:
        #         return redirect(self.get_full_url(request) + self.reverse_subpage("subscription_error"))

    @route(r"^complete/$")
    def post_purchase_cleanup(self, request):
        """
        Present a thank you page and run any wrapup activites that are required.
        """

        # try:
        session = stripe.checkout.Session.retrieve(request.GET.get("session_id"))
        customer = customer = stripe.Customer.retrieve(session.customer)
        # TODO: Create a Django user and associate ^ this

        return self.render(
            request,
            context_overrides={"customer": customer},
            template="app/post_purchase_cleanup.html",
        )
        # except:
        #     if settings.DEBUG is False:
        #         return redirect(self.get_full_url(request) + self.reverse_subpage("subscription_error"))

    @route(r"^error/$")
    def subscription_error(self, request):
        """
        Present a thank you page and run any wrapup activites that are required.
        """

        return self.render(
            request,
            context_overrides={"error": True},
            template="app/subscription_error.html",
        )
