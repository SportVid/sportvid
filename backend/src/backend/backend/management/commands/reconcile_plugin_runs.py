from django.core.management.base import BaseCommand

from backend.plugin_runs import recover_plugin_runs, wait_for_workers


class Command(BaseCommand):
    help = (
        "Mark plugin runs whose Celery task is gone (RUNNING/WAITING, held by no worker) as UNKNOWN "
        "and start the interrupted ones that qualify again (see backend/plugin_runs.py)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--wait-for-workers",
            type=float,
            default=20.0,
            help="Seconds to wait for a Celery worker of every queue to answer (default: 20).",
        )

    def handle(self, *args, **options):
        wait_for_workers(options["wait_for_workers"])
        marked, requeued = recover_plugin_runs()
        self.stdout.write(f"{marked} plugin runs set to UNKNOWN, {requeued} re-queued")
