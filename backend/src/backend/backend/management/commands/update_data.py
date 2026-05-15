from django.core.management.base import BaseCommand
from django.conf import settings

from data.manager import DataManager


class Command(BaseCommand):
    help = "..."

    def add_arguments(self, parser):
        parser.add_argument("--data_ids", nargs="+", type=str)

    def handle(self, *args, **options):
        manager = DataManager("/predictions/")
        for data_id in options["data_ids"]:
            try: data = manager.load(data_id)
            except Exception as e:
                print(data_id)
                raise e
            with manager.create_data(data.type, data_id=data_id) as data_out:
                if data.type == "ScalarData":
                    data_out.y = data.y
                    data_out.time = data.time
                    data_out.delta_time = data.delta_time
                elif data.type == "ShotsData":
                    data_out.shots = data.shots
                elif data.type == "HistData":
                    data_out.hist = data.hist
                    data_out.time = data.time
                    data_out.delta_time = data.delta_time
                elif data.type == "RGBData":
                    data_out.colors = data.colors
                    data_out.time = data.time
                    data_out.delta_time = data.delta_time
                elif data.type == "ImagesData":
                    data_out.images = data.images
                else:
                    self.stdout.write(self.style.ERROR(f"Unkonwn data type {data.type}"))
