# Generated by Django 4.2 on 2024-01-16 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0075_alter_membershipplanprice_products_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="membershipplanpage",
            name="benefits",
        ),
        migrations.RemoveField(
            model_name="membershipplanprice",
            name="benefits",
        ),
        migrations.AlterField(
            model_name="readingoption",
            name="title",
            field=models.CharField(
                help_text="Visible to potential customers", max_length=150
            ),
        ),
    ]