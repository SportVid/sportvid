import os
from django.core.management.base import BaseCommand, CommandError

from backend.models import SportVidUser, Video
from backend.views import VideoExport


class Command(BaseCommand):
    help = "..."

    def add_arguments(self, parser):
        parser.add_argument("--video_ids", nargs="+")
        parser.add_argument("--user_ids", nargs="+")
        parser.add_argument("--output_folder")

    def handle(self, *args, **options):
        video_dbs =[]
        if options["user_ids"]:
            for user_id in options["user_ids"]:
                print(user_id)
                user = SportVidUser.objects.get(id=user_id)
                video_dbs.extend(Video.objects.filter(owner=user))
        if options["video_ids"]:
            for video_id in options["video_ids"]:
                video_dbs.append(Video.objects.get(video_id))

        video_export_view = VideoExport()
        parameters = {
            "include_category":True,
            "use_timestamps":True,
            "use_seconds":True,
            "merge_timeline":True,
            "split_places":True,
        }

        os.makedirs(options["output_folder"], exist_ok=True)
        for video_db in video_dbs:
            with open(os.path.join(options["output_folder"],f"{video_db.name}.cvs"), "w") as f:
                f.write(video_export_view.export_merged_csv(parameters=parameters, video_db=video_db))
            
