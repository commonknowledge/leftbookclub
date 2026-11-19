from django.db import migrations

FIELDS = [
    "menu_id",
    "sort_order",
    "link_page_id",
    "link_url",
    "url_append",
    "handle",
    "link_text",
]


def copy_items(apps, schema_editor):
    """
    Copy wagtailmenus' main menu items into app.CustomMainMenuItem, which the
    site now uses. Sub-menus are left off so the menu looks the same until an
    editor ticks "Allow sub-menu" on an item. The old rows are left in place.
    """
    OldItem = apps.get_model("wagtailmenus", "MainMenuItem")
    NewItem = apps.get_model("app", "CustomMainMenuItem")
    NewItem.objects.bulk_create(
        NewItem(allow_subnav=False, **{f: getattr(item, f) for f in FIELDS})
        for item in OldItem.objects.all()
    )


def remove_items(apps, schema_editor):
    apps.get_model("app", "CustomMainMenuItem").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0110_custom_main_menu_item"),
    ]

    operations = [
        migrations.RunPython(copy_items, remove_items),
    ]
