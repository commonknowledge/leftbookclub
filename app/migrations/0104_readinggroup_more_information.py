# Generated by Django 4.2 on 2025-05-01 14:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0103_remove_readinggroup_join_contact_link_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="readinggroup",
            name="more_information",
            field=models.TextField(
                blank=True,
                help_text="(Optional) Any extra important information about the group.",
                max_length=1024,
                null=True,
            ),
        ),
    ]
