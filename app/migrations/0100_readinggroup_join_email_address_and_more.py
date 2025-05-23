# Generated by Django 4.2 on 2025-04-29 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0099_readinggroupspage"),
    ]

    operations = [
        migrations.AddField(
            model_name="readinggroup",
            name="join_email_address",
            field=models.EmailField(
                default="joaquim@commonknowledge.coop",
                help_text="An email address to contact the group.",
                max_length=1024,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="readinggroup",
            name="join_contact_link",
            field=models.URLField(
                blank=True,
                help_text="(Optional) A link to view the group or join the event.",
                max_length=1024,
                null=True,
            ),
        ),
    ]
