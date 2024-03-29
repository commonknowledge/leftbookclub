from urllib.parse import urlparse

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page, Site

from app.models import BlogIndexPage, HomePage
from app.models.wagtail import BookIndexPage, MerchandiseIndexPage


class Command(BaseCommand):
    help = "Set up essential pages"

    def add_arguments(self, parser):
        default_base_url = urlparse(settings.BASE_URL)

        parser.add_argument(
            "-H", "--host", dest="host", type=str, default=default_base_url.hostname
        )
        parser.add_argument(
            "-p", "--port", dest="port", type=int, default=default_base_url.port or 80
        )

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            site = Site.objects.get(
                root_page__content_type=ContentType.objects.get_for_model(HomePage)
            )
            home = site.root_page
            print("Site and homepage already set up", site, home)
        except:
            home = HomePage(
                title="Left Book Club",
                slug="leftbookclub",
            )
            root = Page.get_first_root_node()
            root.add_child(instance=home)

            site = Site.objects.get_or_create(
                hostname=options.get("host"),
                port=options.get("port"),
                is_default_site=True,
                site_name="Left Book Club",
                root_page=home,
            )

        # Delete placeholders
        Page.objects.filter(title="Welcome to your new Wagtail site!").all().unpublish()

        # Set up website sections
        def ensure_child_page(page_instance: Page, parent_page=home):
            if (
                page_instance.specific_class.objects.filter(slug=page_instance.slug)
                .descendant_of(parent_page)
                .exists()
                is False
            ):
                parent_page.add_child(instance=page_instance)
            else:
                print("Already exists:", page_instance.specific_class, page_instance)

        ensure_child_page(BlogIndexPage(slug="blog", title="Blog"))
        ensure_child_page(BookIndexPage(slug="books", title="Books"))
        ensure_child_page(MerchandiseIndexPage(slug="merchandise", title="Merchandise"))
