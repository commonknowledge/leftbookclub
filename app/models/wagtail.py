import stripe
from django.conf import settings
from django.db import models
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page
import urllib.parse
from django.shortcuts import redirect


class HomePage(RoutablePageMixin, Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body", classname="full"),
    ]

    @route(r'^$') # will override the default Page serving mechanism
    def pick_product(self, request):
        '''
        Provide a list of products to the template, to start the membership signup flow
        '''

        products = [
            p for p in stripe.Product.list()
            # if p.get("metadata", {}).get("pickable", 0) == 1
        ]

        return self.render(request, context_overrides={
            'products': products
        })

    @route(r"^product/(?P<product_id>.+)/$")
    def pick_price_for_product(self, request, product_id):
        """
        When a product has been selected, present the regular/solidarity options.
        """

        try:
            product = stripe.Product.retrieve(product_id)
            prices = stripe.Price.list(product=product)

            return self.render(
              request,
              context_overrides={
                "product": product,
                "prices": prices,
              }
            )
        except:
            return redirect(self.url + self.reverse_subpage("error"))

    @route(r"^price/(?P<price_id>.+)/$")
    def checkout(self, request, price_id):
        """
        Create a checkout session with a line item of price_id
        """

        try:
            session = stripe.checkout.Session.create(
                line_items=[{ "price": price_id, "quantity": 1 }],
                shipping_address_collection={ "allowed_countries": ["GB"] },
                success_url=urllib.parse.urljoin(self.url, 'complete?session_id={CHECKOUT_SESSION_ID}'),
                cancel_url=urllib.parse.urljoin(self.url, 'error'),
            )

            response = redirect(session.url)
            return response
        except:
            return redirect(self.url + self.reverse_subpage("error"))

    @route(r"^complete/$")
    def post_purchase_cleanup(self, request):
        """
        Present a thank you page and run any wrapup activites that are required.
        """

        try:
            session = stripe.checkout.Session.retrieve(request.args.get('session_id'))
            customer = customer = stripe.Customer.retrieve(session.customer)
            # TODO: Create a Django user and associate ^ this

            return self.render(
              request,
              context_overrides={
                "customer": customer
              }
            )
        except:
            return redirect(self.url + self.reverse_subpage("error"))

    @route(r"^error/$")
    def error(self, request):
        """
        Present a thank you page and run any wrapup activites that are required.
        """

        return self.render(
          request,
          context_overrides={
            "error": True
          }
        )