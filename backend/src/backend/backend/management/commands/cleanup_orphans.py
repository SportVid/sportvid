from django.core.management.base import BaseCommand

from backend.cleanup import cleanup_media_orphans, find_media_orphans


class Command(BaseCommand):
    help = (
        "List the files under MEDIA_ROOT that belong to no video or tracking data row "
        "(older than ORPHAN_CLEANUP_MIN_AGE). Removes them only with --delete."
    )

    def add_arguments(self, parser):
        parser.add_argument("--delete", action="store_true", help="remove the orphans")
        parser.add_argument("--min-age", type=int, default=None,
                            help="seconds an entry must be old (default: ORPHAN_CLEANUP_MIN_AGE)")

    def handle(self, *args, **options):
        for path, size in find_media_orphans(options["min_age"]):
            self.stdout.write(f"{size:>14} {path}")
        count, total = cleanup_media_orphans(delete=options["delete"], min_age_seconds=options["min_age"])
        verb = "removed" if options["delete"] else "found (dry run, use --delete)"
        self.stdout.write(f"{count} orphans, {total} bytes {verb}")
