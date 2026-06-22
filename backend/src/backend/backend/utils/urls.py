import os
import logging

from django.conf import settings


def media_url_to_file(id, ext):
    return "https://sportvid.dshs-koeln.de" + settings.MEDIA_URL + id[0:2] + "/" + id[2:4] + "/" + id + ext

# TODO: fix MEDIA_ROOT path bug.
def media_path_to_file(id, ext):
    logging.error(f'settings.MEDIA_ROOT={settings.MEDIA_ROOT}')
    return os.path.join("/media/", id[0:2], id[2:4], f"{id}{ext}")

# TODO fix MEDIA_ROOT path bug.
def media_dir_to_file(id):
    logging.error(f'settings.MEDIA_ROOT={settings.MEDIA_ROOT}')
    return os.path.join("/media/", id[0:2], id[2:4])
