import djstripe.models
import shopify
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.core import hooks

from app.models.django import User
from app.models.stripe import LBCCustomer, ShippingZone


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("wagtailadmin.css"))


class ShippingAdmin(ModelAdmin):
    model = ShippingZone
    menu_icon = "fa-truck"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    # list_display = ('title', 'author')
    # list_filter = ('author',)
    # search_fields = ('title', 'author')


modeladmin_register(ShippingAdmin)


class CustomerAdmin(ModelAdmin):
    model = User
    menu_label = "Members"  # ditch this to use verbose_name_plural from model
    menu_icon = "fa-users"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "id",
        "shipping_name",
        "_subscribed_product",
        "subscription_status",
        "stripe_customer_id",
    )
    list_filter = (
        "djstripe_customers__subscriptions__status",
        "djstripe_customers__subscriptions__plan__product",
    )
    list_export = (
        "shipping_name",
        "shipping_line_1",
        "shipping_line_1",
        "shipping_line_2",
        "shipping_city",
        "shipping_country",
        "shipping_zip",
    )
    export_filename = "lbc_members"

    base_url_path = "membership-list"

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Only show members who have their own membership, not gift membership
        return qs.filter(
            djstripe_customers__isnull=False,
            djstripe_customers__subscriptions__isnull=False,
            djstripe_customers__shipping__isnull=False,
            # djstripe_customers__subscriptions__status__in=('active', 'trialing', ),
        )


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(CustomerAdmin)


def create_shopify_order(
    self, user, variant_id, quantity=1, tags=["Membership Shipment"]
):
    o = shopify.Order()
    o.line_items = [{"variant_id": variant_id, "quantity": quantity}]
    o.financial_status = "paid"
    o.email = self.user.primary_email
    c = shopify.Customer.search(email=o.email)
    o.customer = {"id": c[0].id}
    o.send_receipt = False
    o.send_fulfillment_receipt = False
    # TODO: convert Shipping address from Stripe to Shopify format
    o.shipping_address = {
        "address1": "1 Byers Road",
        "address2": "Flat 4/2",
        "city": "Glasgow",
        "country": "United Kingdom",
        "zip": "G115RD",
        "name": "Jan Baykara",
        "country_code": "GB",
    }
    o.tags = tags
    return o
