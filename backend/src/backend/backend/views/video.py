import os
import imageio
import json
import uuid
import logging
import tarfile

from pathlib import Path
from urllib.parse import urlparse

from django.views import View
from django.http import JsonResponse
from django.conf import settings

from celery.app.control import Control
from sportvid.celery import app as celery_app

from backend.plugin_manager import PluginManager
from backend.utils import (
    download_file,
    media_url_to_file,
    media_dir_to_file,
    media_path_to_file
)
from backend.models import Video

from utils.video_converter import convert_to_hls
from utils.helper import remove_file, remove_dir
from backend.tasks.convert_video import convert_video_to_hls, convert_video_to_fmp4


logger = logging.getLogger(__name__)


def parse_number(val):
    try:
        return float(val.replace(',', '.')) if val else None
    except ValueError:
        return None
            
                
class VideoUpload(View):
    def submit_analyse(self, plugins, **kwargs):
        plugin_manager = PluginManager()
        for plugin in plugins:
            plugin_manager(plugin, **kwargs)

    def post(self, request):
        if not request.user.is_authenticated:
            logger.error("VideoUpload::not_authenticated")
            return JsonResponse(
                {"status": "error", "type": "not_authenticated"}, status=500
            )
        try:
            video_id_uuid = uuid.uuid4()
            video_id = video_id_uuid.hex

            if "file" in request.FILES:
                output_dir = media_dir_to_file(video_id)
                download_result = download_file(
                    output_dir=output_dir,
                    output_name=video_id,
                    file=request.FILES["file"],
                    max_size=request.user.max_video_size,
                    extensions=(".mkv", ".mp4", ".ogv"),
                )

                if download_result["status"] != "ok":
                    logger.error("VideoUpload::failed")
                    return JsonResponse(download_result, status=500)

                path = Path(request.FILES["file"].name)
                ext = "".join(path.suffixes)
                
                file_path = download_result.get('path', "")

                field_length = parse_number(request.POST.get("fieldLength"))
                field_width = parse_number(request.POST.get("fieldWidth"))
                if not field_length: field_length = 105.
                if not field_width: field_width = 68.

                # schedule conversion & analysis asynchronously
                analyzers = request.POST.get("analyser", "").split(",") if request.POST.get("analyser") else []

                video_db = Video.objects.create(
                    name=request.POST.get("title"),
                    id=video_id_uuid,
                    file=video_id_uuid,
                    file_size=request.FILES["file"].size,
                    ext=ext,
                    owner=request.user,
                    field_length=field_length,
                    field_width=field_width,
                    division=request.POST.get("division"),
                    current_position=request.POST.get("currentPosition"),
                    total_number_of_teams=request.POST.get("totalNumberofTeams"),
                    age_group=request.POST.get("ageGroup"),
                    sport=request.POST.get("sport"),
                    status=Video.STATUS_PROCESSING,
                )
                # schedule conversion & analysis asynchronously
                analyzers = []
                try: analyzers = request.POST.get("analyser").split(",")
                except Exception: analyzers = []

                # pass original ext (e.g., .mp4) to the task
                task = convert_video_to_hls.apply_async((video_db.id.hex, ext, analyzers))
                # convert_video_to_hls((video_db.id.hex, ext, analyzers))
                # task = convert_video_to_fmp4.apply_async((video_db.id.hex, ext, analyzers))
                
                video_db.task_id = task.id
                video_db.save(update_fields=["task_id"])

                request.user.used_storage_size += request.FILES["file"].size
                request.user.save()

                video_id_hex = video_db.id.hex if not video_db.file.hex else video_db.id.hex
                return JsonResponse(
                    {
                        "status": "ok",
                        "entries": [
                            {
                                "id": video_id,
                                **video_db.to_dict(),
                                "url": media_url_to_file(video_id_hex, video_db.ext),
                            }
                        ],
                    }
                )

            return JsonResponse({"status": "error"}, status=500)

        except Exception:
            logger.exception("Video upload by user failed")
            return JsonResponse({"status": "error"}, status=500)


class VideoList(View):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=500)
            entries = []
            for video in Video.objects.filter(owner=request.user):
                entries.append(video.to_dict())
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception as e:
            logger.exception("Error listing videos")
            return JsonResponse({"status": "error"}, status=500)


class VideoGet(View):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=500)

            entries = []
            for video in Video.objects.filter(id=request.GET.get("id"), owner=request.user):
                video_id_hex = video.id.hex if not video.file else video.file.hex
                entries.append(
                    {
                        **video.to_dict(),
                        "url": media_url_to_file(video_id_hex, video.ext),
                    }
                )
            if len(entries) != 1:
                return JsonResponse({"status": "error"}, status=500)
            return JsonResponse({"status": "ok", "entry": entries[0]})
        except Exception:
            logger.exception("Failed to get video")
            return JsonResponse({"status": "error"}, status=500)


class VideoRename(View):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=500)
            try:
                body = request.body.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                body = request.body

            try:
                data = json.loads(body)
            except Exception as e:
                return JsonResponse({"status": "error"}, status=500)

            if "id" not in data:
                return JsonResponse(
                    {"status": "error", "type": "missing_values"}, status=500
                )
            if "name" not in data:
                return JsonResponse(
                    {"status": "error", "type": "missing_values"}, status=500
                )
            if not isinstance(data.get("name"), str):
                return JsonResponse(
                    {"status": "error", "type": "wrong_request_body"}, status=500
                )

            try:
                video_db = Video.objects.get(id=data.get("id"))
            except Video.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "type": "not_exist"}, status=500
                )

            video_db.name = data.get("name")
            video_db.save()
            return JsonResponse({"status": "ok", "entry": video_db.to_dict()})
        except Exception:
            logger.exception("Failed to rename video")
            return JsonResponse({"status": "error"}, status=500)


class VideoDelete(View):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=500)
            try:
                body = request.body.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                body = request.body

            try:
                data = json.loads(body)
            except Exception as e:
                return JsonResponse({"status": "error"}, status=500)
            
            video = Video.objects.filter(id=data.get("id"), owner=request.user).first()
            if not video:
                return JsonResponse({"status": "error"}, status=500)

            # Revoke the conversion task if still running.
            # terminate=False: just mark as revoked; the task polls the DB and
            # exits cleanly when it sees the video is gone (avoids SIGTERM/SIGKILL
            # causing Celery's pool to enter a restart cascade).
            if video.task_id:
                celery_app.control.revoke(video.task_id, terminate=False)

            file_size = video.file_size
            video_id_hex = video.id.hex
            count, _ = Video.objects.filter(id=video.id, owner=request.user).delete()

            if count:
                # Clean up files on disk
                try:
                    output_dir = media_dir_to_file(video_id_hex)
                    remove_dir(f"{output_dir}{video_id_hex}")
                    for ext in (video.ext, ".mp4", ".mkv", ".ogv"):
                        remove_file(media_path_to_file(video_id_hex, ext))
                except Exception:
                    logger.exception("Failed to clean up video files after delete")

                request.user.used_storage_size = max(0, request.user.used_storage_size - file_size)
                request.user.save()
                return JsonResponse({"status": "ok"})

            return JsonResponse({"status": "error"}, status=500)
        except Exception:
            logger.exception("Failed to delete video")
            return JsonResponse({"status": "error"}, status=500)
