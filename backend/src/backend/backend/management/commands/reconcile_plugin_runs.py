import time

from django.core.management.base import BaseCommand

from backend.plugin_runs import reconcile_plugin_runs


class Command(BaseCommand):
    help = "Mark plugin runs whose Celery task is gone (RUNNING/WAITING, held by no worker) as UNKNOWN."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wait-for-workers",
            type=float,
            default=20.0,
            help="Seconds to wait for at least one Celery worker to answer (default: 20).",
        )

    def handle(self, *args, **options):
        from sportvid.celery import app

        deadline = time.monotonic() + options["wait_for_workers"]
        while True:
            try:
                if app.control.inspect().ping():
                    break
            except Exception:
                pass
            if time.monotonic() >= deadline:
                break
            time.sleep(2)

        changed = reconcile_plugin_runs()
        self.stdout.write(f"{changed} plugin runs set to UNKNOWN")
