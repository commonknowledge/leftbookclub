from urllib.parse import urlparse

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page, Site

from app.models import BlogIndexPage, HomePage
from app.models.wagtail import BookIndexPage


class Command(BaseCommand):
    help = "Set up essential pages"

    @transaction.atomic
    def handle(self, *args, **options):
        Page.objects.all().delete()
