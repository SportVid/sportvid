import shutil
import os
from django.core.management.base import BaseCommand
from django.conf import settings

from backend.utils import urls


class Command(BaseCommand):
    help = "Move video files to new location"

    def handle(self, *args, **options):
        for f in os.listdir(settings.MEDIA_ROOT):
            file_path = os.path.join(settings.MEDIA_ROOT, f)
            if len(os.path.splitext(f)[0]) == 32 and os.path.splitext(file_path)[1].lower() in [".mp4"]:
                print(file_path)
                output_dir = urls.media_dir_to_file(os.path.splitext(f)[0])
                output_path = urls.media_path_to_file(os.path.splitext(f)[0], os.path.splitext(f)[1].lower())
                print(f"{file_path} {output_dir} {output_path}")
                os.makedirs(output_dir, exist_ok=True)
                shutil.move(file_path, output_path)
