import stripe
from django.conf import settings
from django.db import models
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page

stripe.api_key = settings.STRIPE_API_KEY


class HomePage(RoutablePageMixin, Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body", classname="full"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        products = [
            p
            for p in stripe.Product.list()
            if p.get("metadata", {}).get("pickable", 0) == 1
        ]
        context["products"] = products

    @route(r"^/product/([a-zA-Z0-9]+)$")
    def product_variant_picker(self, request, product_id):
        """
        When a product has been selected, present the regular/solidarity options.
        """

        product = stripe.Product.retrieve(product_id)
        prices = stripe.Price.list(product=product)

        return self.render(
            request, context_overrides={"product": product, "prices": prices}
        )

    @route(r"^/price/([a-zA-Z0-9]+)$")
    def redirect_to_stripe_checkout(self, request, price_id):

        """
        Create a checkout session with a line item of price_id
        """

        stripe.PaymentLink.create(
            line_items=[{"price": price_id, "quantity": 1}],
            shipping_address_collection={"allowed_countries": ["GB"]},
            after_completion={"type": "redirect"},
        )

        # TODO: Generate checkout URL
        # - Shipping
        # - Redirect back to website config
        # - CHECKOUT_SESSION_ID
        # TODO: Redirect user to URL

    @route(r"^/complete/([a-zA-Z0-9]+)$")
    def post_purchase_cleanup(self, request, price_id):
        """
        When a product has been selected, present the regular/solidarity options.
        """

        # TODO: Get the customer from the CHECKOUT_SESSION_ID
        # TODO: Create a Django user and associate ^ this
