import os
import logging

from django.conf import settings


def media_url_to_file(id, ext):
    return "https://sportvid.dshs-koeln.de" + settings.MEDIA_URL + id[0:2] + "/" + id[2:4] + "/" + id + ext

def media_path_to_file(id, ext):
    logging.error(settings.MEDIA_ROOT)
    return os.path.join(settings.MEDIA_ROOT, id[0:2], id[2:4], f"{id}{ext}")

def media_dir_to_file(id):
    return os.path.join(settings.MEDIA_ROOT, id[0:2], id[2:4])
