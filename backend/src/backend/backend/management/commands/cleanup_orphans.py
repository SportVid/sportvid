from django.core.management.base import BaseCommand

from backend.cleanup import (
    cleanup_media_orphans,
    cleanup_prediction_orphans,
    find_media_orphans,
    find_prediction_orphans,
)

STORES = {
    "media": (find_media_orphans, cleanup_media_orphans),
    "predictions": (find_prediction_orphans, cleanup_prediction_orphans),
}


class Command(BaseCommand):
    help = (
        "List the files under MEDIA_ROOT that belong to no video or tracking data row, and under "
        "DATA_OUTPUT_PATH that belong to no plugin result (older than ORPHAN_CLEANUP_MIN_AGE; "
        "results at least PLUGIN_RUN_TIMEOUT). Removes them only with --delete."
    )

    def add_arguments(self, parser):
        parser.add_argument("--delete", action="store_true", help="remove the orphans")
        parser.add_argument("--min-age", type=int, default=None,
                            help="seconds an entry must be old (default: ORPHAN_CLEANUP_MIN_AGE)")
        parser.add_argument("--store", choices=[*STORES, "all"], default="all",
                            help="which folder to check (default: all)")

    def handle(self, *args, **options):
        stores = list(STORES) if options["store"] == "all" else [options["store"]]
        verb = "removed" if options["delete"] else "found (dry run, use --delete)"
        for store in stores:
            find, cleanup = STORES[store]
            for path, size in find(options["min_age"]):
                self.stdout.write(f"{size:>14} {path}")
            count, total = cleanup(delete=options["delete"], min_age_seconds=options["min_age"])
            self.stdout.write(f"{store}: {count} orphans, {total} bytes {verb}")
