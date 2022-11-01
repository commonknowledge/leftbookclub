from django.core import management
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run background processes"

    def handle(self, *args, **options):
        # Start the one-off job queue (`django_dbq`)
        management.call_command("worker", rate_limit=30)
        # Start the periodic job queue (`groundwork` via `schedule`)
        management.call_command("run_cron_tasks")
