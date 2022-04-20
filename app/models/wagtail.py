import urllib.parse

import shopify
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.dispatch import receiver
from django.http.response import Http404
from django.shortcuts import redirect
from django_countries import countries
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.models import AbstractImage, AbstractRendition
from wagtail.search import index

from app.forms import CountrySelectorForm
from app.models.blocks import ArticleContentStream
from app.shopify_webhook.signals import products_create
from app.utils.cache import django_cached
from app.utils.shopify import metafields_to_dict
from app.views import (
    CheckoutSessionCompleteView,
    CreateCheckoutSessionView,
    ShippingCostView,
)

from .stripe import LBCProduct, ShippingZone


class HomePage(RoutablePageMixin, Page):
    body = RichTextField(blank=True)
    show_in_menus_default = True

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
    @route(r"^product/(?P<product_id>.+)/(?P<country_id>.+)/$")
    def pick_price_for_product(self, request, product_id, country_id="GB"):
        """
        When a product has been selected, select shipping country.
        """

        product = LBCProduct.objects.get(id=product_id)

        return self.render(
            request,
            context_overrides={
                "product": product,
                "default_country_code": country_id,
                "country_selector_form": CountrySelectorForm(
                    initial={"country": country_id}
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
            return redirect(
                urllib.parse.urljoin(
                    self.get_full_url(request),
                    self.reverse_subpage(
                        "pick_price_for_product",
                        kwargs={"product_id": product_id, "country_id": country},
                    ),
                )
            )

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
                # By default, customer details aren't updated, but we want them to be.
                customer_update={
                    "shipping": "auto",
                    "address": "auto",
                    "name": "auto",
                },
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


class CustomImage(AbstractImage):

    # Making blank / null explicit because you *really* need alt text
    alt_text = models.CharField(
        max_length=1024,
        blank=False,
        null=False,
        default="",
        help_text="Describe this image as literally as possible. If you can close your eyes, have someone read the alt text to you, and imagine a reasonably accurate version of the image, you're on the right track.",
    )

    admin_form_fields = (
        "file",
        "alt_text",
        "title",
    )


class ImageRendition(AbstractRendition):
    image = models.ForeignKey(
        CustomImage, on_delete=models.CASCADE, related_name="renditions"
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)


class BlogIndexPage(Page):
    """
    Define blog index page.
    """

    show_in_menus_default = True

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro", classname="full")]


class BlogPage(Page):
    """
    Define blog detail page.
    """

    show_in_menus_default = True

    intro = models.CharField(max_length=250)

    feed_image = models.ForeignKey(
        CustomImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = ArticleContentStream()

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        StreamFieldPanel("body", classname="full"),
        ImageChooserPanel("feed_image"),
    ]


class InformationPage(Page):
    show_in_menus_default = True

    cover_image = models.ForeignKey(
        CustomImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    body = ArticleContentStream()

    content_panels = Page.content_panels + [
        ImageChooserPanel("cover_image"),
        StreamFieldPanel("body", classname="full"),
    ]


class BookIndexPage(Page):
    body = ArticleContentStream()

    content_panels = Page.content_panels + [
        StreamFieldPanel("body", classname="full"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        products = [
            {
                "page": p,
                "product": p.shopify_product,
                "metafields": p.shopify_product_metafields,
            }
            for p in BookPage.objects.live()
            .descendant_of(self)
            .filter(published_date__isnull=False)
            .order_by("-published_date")
        ]
        context["products"] = products
        return context


def shopify_product_id_key(page):
    return page.shopify_product_id


class BaseShopifyProductPage(Page):
    class Meta:
        abstract = True

    # TODO: Autocomplete this in future?
    shopify_product_id = models.CharField(max_length=300, blank=False, null=False)

    content_panels = Page.content_panels + [FieldPanel("shopify_product_id")]

    @classmethod
    def get_for_product(cls, id=None, product=None, handle=None):
        if product is not None:
            id = product.id

        if id is not None:
            # Check if it exists by ID
            page = cls.objects.filter(shopify_product_id=id).first()
            if page is not None:
                return page

            if product is None:
                # Query by ID
                with shopify.Session.temp(
                    settings.SHOPIFY_DOMAIN,
                    "2021-10",
                    settings.SHOPIFY_PRIVATE_APP_PASSWORD,
                ):
                    product = shopify.Product.find(id)

        if product is None and handle is not None:
            # Query by handle
            with shopify.Session.temp(
                settings.SHOPIFY_DOMAIN,
                "2021-10",
                settings.SHOPIFY_PRIVATE_APP_PASSWORD,
            ):
                product = shopify.Product.find(handle=handle)

        if product is None:
            return None

        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            metafields = product.metafields()
            metafields = metafields_to_dict(metafields)

            # Create new page
            page = cls.create_instance_for_product(product, metafields)
            cls.get_common_ancestor().add_child(instance=page)

            return page

    @classmethod
    def create_instance_for_product(cls, product, metafields):
        return cls(
            slug=product.attributes.get("handle"),
            title=product.title,
            shopify_product_id=product.id,
        )

    @property
    @django_cached("shopify_product", get_key=shopify_product_id_key)
    def shopify_product(self):
        return self.latest_shopify_product

    @property
    def latest_shopify_product(self):
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            return shopify.Product.find(self.shopify_product_id)

    @property
    @django_cached("shopify_product_metafields", get_key=shopify_product_id_key)
    def shopify_product_metafields(self):
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            metafields = self.shopify_product.metafields()
            return metafields_to_dict(metafields)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["product"] = self.shopify_product
        context["metafields"] = self.shopify_product_metafields
        return context

    @classmethod
    def sync_shopify_products_to_pages(cls):
        print("sync_shopify_products_to_pages")
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            cache.clear()
            book_ids = shopify.CollectionListing.find(
                settings.SHOPIFY_COLLECTION_ID
            ).product_ids()
            for book in book_ids:
                BookPage.get_for_product(book)

            # TODO: also list merch
            # products = shopify.Product.find(collection=settings.SHOPIFY_COLLECTION_ID)
            # for product in products:
            #     ShopifyProductPage.get_for_product(id=product.id)


class MerchandisePage(BaseShopifyProductPage):
    pass


class BookPage(BaseShopifyProductPage):
    published_date = models.DateField(null=True, blank=True)

    content_panels = BaseShopifyProductPage.content_panels + [
        FieldPanel("published_date")
    ]

    @classmethod
    def get_common_ancestor(cls):
        return BookIndexPage.objects.first()

    @classmethod
    def create_instance_for_product(cls, product, metafields):
        return cls(
            slug=product.attributes.get("handle"),
            title=product.title,
            shopify_product_id=product.id,
            published_date=metafields.get("published_date", None),
        )

    class Meta:
        ordering = ["published_date"]


@receiver(products_create)
def sync(*args, **kwargs):
    print(args, kwargs)
    BaseShopifyProductPage.sync_shopify_products_to_pages()
