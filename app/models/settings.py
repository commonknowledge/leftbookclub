from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.edit_handlers import StreamFieldPanel
from wagtail.admin.menu import MenuItem
from wagtail.contrib.settings.models import BaseSetting, register_setting
from wagtail.core import hooks
from wagtailautocomplete.edit_handlers import AutocompletePanel

from app.models.wagtail import BookPage, create_streamfield


@register_setting(icon="users")
class MembershipJourney(BaseSetting):
    welcome_content = create_streamfield()
    panels = [StreamFieldPanel("welcome_content")]


def settings_path(custom_settings_cls):
    return f"/admin/settings/{custom_settings_cls._meta.app_label}/{custom_settings_cls._meta.model_name}"
