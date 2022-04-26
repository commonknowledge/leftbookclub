import urllib.parse
from importlib.metadata import metadata
from urllib.parse import urlencode

import djstripe.models
import shopify
import stripe
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.dispatch import receiver
from django.http.response import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.html import strip_tags
from django_countries import countries
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page
from wagtail.core.rich_text import get_text_for_indexing
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.models import AbstractImage, AbstractRendition
from wagtail.search import index
from wagtailseo.models import SeoMixin, SeoType, TwitterCard

from app.forms import CountrySelectorForm
from app.models.blocks import ArticleContentStream
from app.shopify_webhook.signals import products_create
from app.utils import include_keys
from app.utils.cache import django_cached
from app.utils.shopify import metafields_to_dict
from app.views import CreateCheckoutSessionView, ShippingCostView

from .stripe import LBCProduct, ShippingZone


class SeoMetadataMixin(SeoMixin, Page):
    class Meta:
        abstract = True

    promote_panels = SeoMixin.seo_panels

    seo_image_sources = ["og_image"]  # Explicit sharing image

    seo_description_sources = [
        "search_description",  # Explicit sharing description
    ]

    @property
    def seo_description(self) -> str:
        """
        Middleware for seo_description_sources
        """
        for attr in self.seo_description_sources:
            if hasattr(self, attr):
                text = getattr(self, attr)
                if text:
                    # Strip HTML if there is any
                    return get_text_for_indexing(text)
        return ""


class IndexPageSeoMixin(SeoMetadataMixin):
    class Meta:
        abstract = True

    seo_content_type = SeoType.WEBSITE
    seo_twitter_card = TwitterCard.SUMMARY
    promote_panels = SeoMixin.seo_panels


class ArticleSeoMixin(SeoMetadataMixin):
    class Meta:
        abstract = True

    seo_content_type = SeoType.ARTICLE
    seo_twitter_card = TwitterCard.LARGE
    promote_panels = SeoMixin.seo_panels


class HomePage(IndexPageSeoMixin, RoutablePageMixin, Page):
    body = RichTextField(blank=True)
    show_in_menus_default = True

    content_panels = Page.content_panels + [
        FieldPanel("body", classname="full"),
    ]

    seo_description_sources = IndexPageSeoMixin.seo_description_sources + ["body"]

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
        gift_mode = request.GET.get("gift_mode", None)

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
        price = product.basic_price
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

        checkout_args = dict(
            mode="subscription",
            line_items=[
                {
                    # Membership
                    "price": price.id,
                    "quantity": 1,
                },
                {
                    # Shipping
                    "price_data": {
                        "currency": zone.rate_currency,
                        "product_data": {"name": f"Shipping to {zone.nickname}"},
                        "unit_amount_decimal": zone.rate.amount * 100,
                        # running on the same payment schedule as the membership
                        "recurring": include_keys(
                            price.recurring,
                            (
                                "interval",
                                "interval_count",
                            ),
                        ),
                        "metadata": {"shipping": True},
                    },
                    "quantity": 1,
                },
            ],
            # By default, customer details aren't updated, but we want them to be.
            customer_update={
                "shipping": "auto",
                "address": "auto",
                "name": "auto",
            },
            metadata={},
        )
        callback_url_args = {}

        if gift_mode is not None and gift_mode is not False:
            callback_url_args["gift_mode"] = True
            checkout_args["metadata"]["gift_mode"] = True
        else:
            checkout_args["shipping_address_collection"] = {
                "allowed_countries": zone.country_codes
            }

        checkout_args["success_url"] = urllib.parse.urljoin(
            self.get_full_url(request),
            reverse_lazy("member_signup_complete")
            + "?session_id={CHECKOUT_SESSION_ID}&"
            + urlencode(callback_url_args),
        )
        checkout_args["cancel_url"] = urllib.parse.urljoin(
            self.get_full_url(request),
            self.reverse_subpage("pick_product") + "?" + urlencode(callback_url_args),
        )

        return CreateCheckoutSessionView.as_view(context=checkout_args)(request)

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


class BlogIndexPage(IndexPageSeoMixin, Page):
    """
    Define blog index page.
    """

    show_in_menus_default = True

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro", classname="full")]

    seo_description_sources = IndexPageSeoMixin.seo_description_sources + ["intro"]


class BlogPage(ArticleSeoMixin, Page):
    """
    Define blog detail page.
    """

    show_in_menus_default = True

    intro = RichTextField(max_length=250)

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

    seo_description_sources = ArticleSeoMixin.seo_description_sources + [
        "intro",
        "body",
    ]

    seo_image_sources = ArticleSeoMixin.seo_image_sources + ["feed_image"]


class InformationPage(ArticleSeoMixin, Page):
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

    seo_description_sources = ArticleSeoMixin.seo_description_sources + ["body"]

    seo_image_sources = ArticleSeoMixin.seo_image_sources + ["cover_image"]


class BookIndexPage(IndexPageSeoMixin, Page):
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

    seo_description_sources = ArticleSeoMixin.seo_description_sources + ["body"]


def shopify_product_id_key(page):
    return page.shopify_product_id


class BaseShopifyProductPage(ArticleSeoMixin, Page):
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
            BookIndexPage.objects.first().add_child(instance=page)

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
    def latest_shopify_product(self) -> shopify.ShopifyResource:
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            try:
                product = shopify.Product.find(self.shopify_product_id)
                return product
            except:
                return None

    @property
    @django_cached("shopify_product_metafields", get_key=shopify_product_id_key)
    def shopify_product_metafields(self):
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            try:
                metafields = self.shopify_product.metafields()
                return metafields_to_dict(metafields)
            except:
                return {}

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

    @property
    def seo_description(self) -> str:
        try:
            tags = strip_tags(self.shopify_product.body_html).replace("\n", "")
            return tags
        except:
            return ""

    @property
    def seo_image_url(self) -> str:
        """
        Middleware for seo_image_sources
        """
        try:
            image = self.shopify_product.images[0].src
            return image
        except:
            return ""


class MerchandisePage(BaseShopifyProductPage):
    pass


class BookPage(BaseShopifyProductPage):
    published_date = models.DateField(null=True, blank=True)

    content_panels = BaseShopifyProductPage.content_panels + [
        FieldPanel("published_date")
    ]

    @property
    def common_ancestor(cls):
        book = BookIndexPage.objects.first()
        return book

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
