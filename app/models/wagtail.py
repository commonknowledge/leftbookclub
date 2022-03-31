import urllib.parse

from django.shortcuts import redirect
from django_countries import countries
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page

from app.forms import CountrySelectorForm
from app.views import (
    CheckoutSessionCompleteView,
    CreateCheckoutSessionView,
    ShippingCostView,
)

from .stripe import LBCProduct, ShippingZone


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
        When a product has been selected, select shipping country.
        """

        product = LBCProduct.objects.get(id=product_id)
        default_country_code = "GB"

        return self.render(
            request,
            context_overrides={
                "product": product,
                "default_country_code": default_country_code,
                "country_selector_form": CountrySelectorForm(
                    initial={"country": default_country_code}
                ),
                "url_pattern": ShippingCostView.url_pattern,
            },
            template="app/pick_price_for_product.html",
        )

    @route(r"^checkout/(?P<product_id>.+)/$")
    def checkout(self, request, product_id):
        """
        Create a checkout session with a line item of price_id
        """

        country = request.GET.get("country", None)

        if country is None:
            return redirect(
                urllib.parse.urljoin(
                    self.get_full_url(request),
                    self.reverse_subpage(
                        "pick_price_for_product", kwargs={"product_id": product_id}
                    ),
                )
            )

        product = LBCProduct.objects.get(id=product_id)
        price = product.get_prices_for_country(
            iso_a2=country, recurring__interval="month"
        ).first()
        zone = ShippingZone.get_for_country(country)

        if price is None:
            print(
                "!!!!! No shipping option is defined for",
                country,
                "which resolves to zone",
                zone,
                ". Using basic price instead.",
            )
            price = product.basic_price

        return CreateCheckoutSessionView.as_view(
            context=dict(
                mode="subscription",
                shipping_address_collection={"allowed_countries": zone.country_codes},
                line_items=[{"price": price.id, "quantity": 1}],
                success_url=urllib.parse.urljoin(
                    self.get_full_url(request),
                    "complete?session_id={CHECKOUT_SESSION_ID}",
                ),
                cancel_url=urllib.parse.urljoin(
                    self.get_full_url(request), self.reverse_subpage("pick_product")
                ),
            )
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
