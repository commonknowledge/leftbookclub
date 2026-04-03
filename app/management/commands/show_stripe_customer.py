import json

import djstripe.models
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Print djstripe Customer details for a given email address"

    def add_arguments(self, parser):
        parser.add_argument("email", type=str)

    def handle(self, *args, **options):
        email = options["email"]
        customers = djstripe.models.Customer.objects.filter(email=email)

        if not customers.exists():
            self.stderr.write(f"No customer found with email: {email}")
            return

        for customer in customers:
            self.stdout.write(f"id:       {customer.id}")
            self.stdout.write(f"email:    {customer.email}")
            self.stdout.write(f"name:     {customer.name}")
            self.stdout.write(f"phone:    {customer.phone}")
            self.stdout.write(f"address:  {json.dumps(customer.address, indent=2)}")
            self.stdout.write(f"shipping: {json.dumps(customer.shipping, indent=2)}")
            self.stdout.write(f"synced:   {customer.djstripe_updated}")
            self.stdout.write("")
