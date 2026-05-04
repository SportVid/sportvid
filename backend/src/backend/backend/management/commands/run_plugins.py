import json
from multiprocessing import Pool
from contextlib import nullcontext
from django.core.management.base import BaseCommand, CommandError

from backend.models import Video
from backend.plugin_manager import PluginManager


def job(args):
    video_id = args["video_id"]
    plugin_manager = args["plugin_manager"]
    plugin = args["plugin"]
    parameters = args["parameters"]
    dry_run = args["dry_run"]

    try:
        video_db = Video.objects.get(pk=video_id)
        user_db = video_db.owner
    except Video.DoesNotExist:
        raise CommandError('Poll "%s" does not exist' % video_id)

    result = plugin_manager(
        plugin,
        parameters=parameters,
        user=user_db,
        video=video_db,
        run_async=False,
        dry_run=dry_run,
    )

    return {"video_id": video_id, "plugin": plugin, **result}


class Command(BaseCommand):
    help = "..."

    def add_arguments(self, parser):
        parser.add_argument("--video_ids", nargs="+", type=str)
        parser.add_argument("--plugin", type=str)
        parser.add_argument("--num_threads", type=int, default=2)
        parser.add_argument("--parameters", type=str)
        parser.add_argument("--output", type=str)
        parser.add_argument("--dry_run", action="store_true")

    def handle(self, *args, **options):
        plugin_manager = PluginManager()
        parameters = []
        if options["parameters"]:
            parameters = json.loads(options["parameters"])

        pool = Pool(options["num_threads"])
        if options["output"]:
            context = open(options["output"], "w")
        else:
            context = nullcontext()
        with context as f:
            for result in pool.imap(
                job,
                [
                    {
                        "video_id": x,
                        "plugin_manager": plugin_manager,
                        "parameters": parameters,
                        "plugin": options["plugin"],
                        "dry_run": options["dry_run"],
                    }
                    for x in options["video_ids"]
                ],
            ):
                if f:
                    f.write(json.dumps(result) + "\n")
                print(result)
            # self.stdout.write(self.style.SUCCESS('Successfully start plugin "%s"'))
