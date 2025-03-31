from datetime import timedelta
from django.core import management
from django.core.management.base import BaseCommand
from groundwork.core.cron import register_cron


class Command(BaseCommand):
    help = "Run background processes"

    def handle(self, *args, **options):
        # Start the one-off job queue (`django_dbq`)
        management.call_command("worker", rate_limit=30)

        # Register cron commands
        def run_ensure_stripe_subscriptions_processed():
            management.call_command(
                "ensure_stripe_subscriptions_processed", dry_run=True
            )

        register_cron(run_ensure_stripe_subscriptions_processed, timedelta(seconds=60))

        # Start the periodic job queue (`groundwork` via `schedule`)
        management.call_command("run_cron_tasks")
        print("Workers have been started.")
