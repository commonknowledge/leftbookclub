import urllib.parse

import stripe
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page

from app.views import CheckoutSessionCompleteView, CreateCheckoutSessionView

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

        product = LBCProduct.objects.get(id=product_id)

        return self.render(
            request,
            context_overrides={"product": product},
            template="app/pick_price_for_product.html",
        )

    @route(r"^checkout/(?P<price_id>.+)/$")
    def checkout(self, request, price_id):
        """
        Create a checkout session with a line item of price_id
        """

        return CreateCheckoutSessionView.as_view(
            context={
                "success_url": urllib.parse.urljoin(
                    self.get_full_url(request),
                    "complete?session_id={CHECKOUT_SESSION_ID}",
                ),
                "cancel_url": urllib.parse.urljoin(
                    self.get_full_url(request), self.reverse_subpage("pick_product")
                ),
                "price_id": price_id,
            }
        )(request)

    @route(r"^complete/$")
    def post_purchase_cleanup(self, request):
        """
        Present a thank you page and run any wrapup activites that are required.
        """

        return CheckoutSessionCompleteView.as_view()(request)

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
