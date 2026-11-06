from django.core.management.base import BaseCommand
from django.db.models import Sum

from backend.models import SportVidUser, TrackingData, Video


class Command(BaseCommand):
    help = (
        "Recompute each user's used_storage_size from their videos and tracking data. "
        "Prints the differences; writes them only with --apply."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="store the recomputed values")

    def handle(self, *args, **options):
        changed = 0
        for user in SportVidUser.objects.order_by("id"):
            videos = Video.objects.filter(owner=user).aggregate(s=Sum("file_size"))["s"] or 0
            tracking = TrackingData.objects.filter(owner=user).aggregate(
                f=Sum("file_size"), m=Sum("meta_file_size")
            )
            actual = videos + (tracking["f"] or 0) + (tracking["m"] or 0)
            if actual == user.used_storage_size:
                continue
            changed += 1
            over = " (over quota)" if actual > user.max_storage_size else ""
            self.stdout.write(f"{user.username}: {user.used_storage_size} -> {actual} bytes{over}")
            if options["apply"]:
                SportVidUser.objects.filter(pk=user.pk).update(used_storage_size=actual)

        verb = "updated" if options["apply"] else "would change (dry run, use --apply)"
        self.stdout.write(f"{changed} users {verb}")
