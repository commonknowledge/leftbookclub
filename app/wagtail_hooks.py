from re import I

import djstripe.models
import shopify
from admin_list_controls.actions import Link, SubmitForm
from admin_list_controls.components import Button, Columns, Panel
from admin_list_controls.filters import BooleanFilter, ChoiceFilter, TextFilter
from admin_list_controls.views import ListControlsIndexView
from django.db.models import Count, Q
from django.templatetags.static import static
from django.utils.html import format_html
from djstripe.enums import SubscriptionStatus
from wagtail import hooks
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail_rangefilter.filters import DateTimeRangeFilter

from app.models.django import User
from app.models.stripe import LBCCustomer, LBCProduct, LBCSubscription, ShippingZone
from app.models.wagtail import MembershipPlanPage, MembershipPlanPrice, ReadingOption
from app.utils import ensure_list
from app.models.wagtail import Event 


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("wagtailadmin.css"))


class ReadingOptionsAdmin(ModelAdmin):
    model = ReadingOption
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    menu_label = "Delivery options"
    menu_icon = "fa-envelop"


modeladmin_register(ReadingOptionsAdmin)


class MembershipOptionsAdmin(ModelAdmin):
    model = MembershipPlanPage
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    menu_icon = "fa-money"
    menu_label = "Plans"


modeladmin_register(MembershipOptionsAdmin)


class ShippingAdmin(ModelAdmin):
    model = ShippingZone
    menu_icon = "fa-truck"
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )


modeladmin_register(ShippingAdmin)


class MultipleChoiceFilter(ChoiceFilter):
    def clean(self, request):
        if self.multiple:
            whitelisted_values = [choice[0] for choice in self.choices]
            values = request.GET.getlist(self.name)
            cleaned_values = [value for value in values if value in whitelisted_values]
            if cleaned_values:
                return cleaned_values
            elif self.default_value:
                # Overwritten part of function
                return ensure_list(self.default_value)
            else:
                return []
        return super().clean(request)


def filter_member_statuses(queryset, values):
    if "active" in values and "expired" in values:
        return queryset
    if "active" in values:
        return queryset.filter(status__in=User.valid_subscription_statuses)
    if "expired" in values:
        return queryset.exclude(status__in=User.valid_subscription_statuses)


class IndexView(ListControlsIndexView):
    def build_list_controls(self):
        config = [
            Panel()(
                Columns()(
                    MultipleChoiceFilter(
                        name="status",
                        label="Member Statuses",
                        multiple=True,
                        choices=[
                            ("active", "Active Members"),
                            ("expired", "Expired Members"),
                        ],
                        default_value="active",
                        apply_to_queryset=filter_member_statuses,
                    ),
                ),
                Button(action=SubmitForm())(
                    "Apply filters",
                ),
            ),
        ]
        return config


class CustomerAdmin(ModelAdmin):
    index_view_class = IndexView
    model = LBCSubscription
    menu_label = "Members"  # ditch this to use verbose_name_plural from model
    menu_icon = "fa-users"
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "recipient_name",
        "primary_product_name",
        "is_active_member",
        "should_upgrade",
    )
    list_export = (
        "recipient_name",
        "recipient_email",
        "primary_product_name",
        "should_upgrade",
        "has_legacy_membership_price",
        "no_shipping_line",
        "non_zero_shipping",
        "is_gift_receiver",
        "is_active_member",
        "status",
        "created",
        "ended_at",
        "shipping_line_1",
        "shipping_line_2",
        "shipping_city",
        "shipping_state",
        "shipping_country",
        "shipping_postcode",
    )
    export_filename = "lbc_members"

    def get_list_filter(self, request):
        if request.GET.get("status") == "expired":
            return (("ended_at", DateTimeRangeFilter),)
        return ()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (
            qs.filter(
                metadata__gift_mode__isnull=True,
            )
            .distinct()
            .select_related("plan__product", "customer__subscriber")
        )


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(CustomerAdmin)


from django.urls import reverse
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from app.models import CircleEvent


class EventIndexView(ListControlsIndexView):
    def build_list_controls(self):
        config = [
            Panel()(
                Button(action=Link(reverse("refresh_circle")))(
                    "Sync new events from Circle.so"
                )
            ),
        ]
        return config


class EventAdmin(ModelAdmin):
    index_view_class = EventIndexView
    model = CircleEvent
    base_url_path = (
        "circle-events"  # customise the URL from default to admin/EventAdmin
    )
    menu_label = "Events"  # ditch this to use verbose_name_plural from model
    menu_icon = "date"
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    ordering = ("-starts_at",)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    add_to_admin_menu = True  # or False to exclude your model from the menu
    list_display = (
        "name",
        "starts_at",
        "location_type",
        "url",
    )
    list_filter = (
        "starts_at",
        "location_type",
    )
    search_fields = (
        "name",
        "in_person_location",
        "body_html",
    )


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(EventAdmin)


class NewEventAdmin(ModelAdmin):
    model = Event
    base_url_path = (
        "new-events"  # customise the URL from default to admin/EventAdmin
    )
    menu_label = "New Events"  # ditch this to use verbose_name_plural from model
    menu_icon = "date"
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    ordering = ("-start_date",)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    add_to_admin_menu = True  # or False to exclude your model from the menu

    list_display = (
        "name",
        "start_date",
        "is_online",
        "online_url",
    )
    list_filter = (
        "start_date",
        "is_online",
    )
    search_fields = (
        "name",
        "in_person_location",
        "body",
    )


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(NewEventAdmin)
