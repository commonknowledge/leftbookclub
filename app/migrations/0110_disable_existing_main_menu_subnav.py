from django.db import migrations


def disable_subnav(apps, schema_editor):
    """
    The header now renders dropdowns for main menu items that have
    "Allow sub-menu for this item" ticked. That field defaults to True, so
    switch it off on existing items to keep the current menu unchanged
    (e.g. so "Blog" doesn't suddenly list every post). Editors opt in per item.
    """
    MainMenuItem = apps.get_model("wagtailmenus", "MainMenuItem")
    MainMenuItem.objects.update(allow_subnav=False)


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0109_menupage_fields"),
        ("wagtailmenus", "0023_remove_use_specific"),
    ]

    operations = [
        migrations.RunPython(disable_subnav, migrations.RunPython.noop),
    ]
