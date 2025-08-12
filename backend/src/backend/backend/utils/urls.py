import os

from django.conf import settings


def media_url_to_file(id, ext):
    return "http://localhost" + settings.MEDIA_URL + id[0:2] + "/" + id[2:4] + "/" + id + ext

def media_path_to_file(id, ext):
    return settings.MEDIA_ROOT + id[0:2] + "/" + id[2:4] + "/" + id + ext

def media_dir_to_file(id):
    return settings.MEDIA_ROOT + id[0:2] + "/" + id[2:4] + "/"
