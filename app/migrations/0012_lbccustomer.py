# Generated by Django 4.0.4 on 2022-04-25 09:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0011_alter_invoice_charge_alter_invoice_customer_and_more"),
        ("app", "0011_alter_blogpage_intro"),
    ]

    operations = [
        migrations.CreateModel(
            name="LBCCustomer",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("djstripe.customer",),
        ),
    ]