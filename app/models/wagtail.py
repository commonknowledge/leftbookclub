import urllib.parse

from django.db import models
from django.shortcuts import redirect
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
from app.views import (
    CheckoutSessionCompleteView,
    CreateCheckoutSessionView,
    ShippingCostView,
)

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


class ArticleSeoMixin(SeoMetadataMixin):
    class Meta:
        abstract = True

    seo_content_type = SeoType.ARTICLE
    seo_twitter_card = TwitterCard.LARGE


class HomePage(SeoMetadataMixin, RoutablePageMixin, Page):
    body = RichTextField(blank=True)
    show_in_menus_default = True

    content_panels = Page.content_panels + [
        FieldPanel("body", classname="full"),
    ]

    promote_panels = SeoMixin.seo_panels

    seo_twitter_card = TwitterCard.SUMMARY

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


class BlogIndexPage(SeoMetadataMixin, Page):
    """
    Define blog index page.
    """

    show_in_menus_default = True

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro", classname="full")]

    promote_panels = SeoMixin.seo_panels

    seo_twitter_card = TwitterCard.SUMMARY


class BlogPage(ArticleSeoMixin, Page):
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

    promote_panels = SeoMixin.seo_panels


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

    promote_panels = SeoMixin.seo_panels
