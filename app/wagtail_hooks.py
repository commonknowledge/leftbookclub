from re import I

import djstripe.models
import shopify
from admin_list_controls.actions import SubmitForm
from admin_list_controls.components import Button, Columns, Panel
from admin_list_controls.filters import BooleanFilter, ChoiceFilter, TextFilter
from admin_list_controls.views import ListControlsIndexView
from django.db.models import Count, Q
from django.templatetags.static import static
from django.utils.html import format_html
from djstripe.enums import SubscriptionStatus
from wagtail import hooks
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from app.models.django import User
from app.models.stripe import LBCCustomer, LBCProduct, LBCSubscription, ShippingZone
from app.models.wagtail import MembershipPlanPage, MembershipPlanPrice
from app.utils import ensure_list


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("wagtailadmin.css"))


class MembershipOptionsAdmin(ModelAdmin):
    model = MembershipPlanPage
    menu_icon = "fa-money"  # change as required
    menu_label = "Plans"


modeladmin_register(MembershipOptionsAdmin)


class PriceOptionsAdmin(ModelAdmin):
    model = MembershipPlanPrice
    menu_label = "Prices"
    menu_icon = "fa-money"  # change as required


modeladmin_register(PriceOptionsAdmin)


class ShippingAdmin(ModelAdmin):
    model = ShippingZone
    menu_icon = "fa-truck"  # change as required
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
    menu_icon = "fa-users"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "recipient_name",
        "primary_product_name",
        "is_active_member",
    )
    list_export = (
        "recipient_name",
        "recipient_email",
        "primary_product_name",
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
