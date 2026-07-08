import re
import json
import uuid
import logging
import tempfile
import tempfile
import time

from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings

from rest_framework import serializers

from backend.models import Video, PluginRun
from backend.plugin_manager import PluginManager
from backend.utils import download_url, download_file, media_url_to_file

from backend.serializers import PluginRunRequestSerializer

logger = logging.getLogger(__name__)


class PluginRunNew(View):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=401)

            raw_parameters = request.POST.get("parameters")
            payload = {
                "plugin": request.POST.get("plugin"),
                "video_id": request.POST.get("video_id"),
                "parameters": json.loads(raw_parameters) if raw_parameters else None,
            }

            serializer = PluginRunRequestSerializer(data=payload)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            output_dir = tempfile.mkdtemp(dir="/tmp")
            file_parameters = {}

            for key, uploaded_file in request.FILES.items():
                m = re.match(r"^file_(.*?)$", key)
                if not m:
                    continue

                data_id_uuid = uuid.uuid4().hex
                download_result = download_file(
                    output_dir=output_dir,
                    output_name=data_id_uuid,
                    file=uploaded_file,
                    max_size=11 * 1024 * 1024 * 1024,
                )

                if download_result.get("status") == "ok":
                    file_parameters[m.group(1)] = {
                        "value": download_result["origin"],
                        "path": download_result["path"],
                    }

            parameters = data["parameters"].copy()
            parameters["_files"] = file_parameters

            video_db = Video.objects.get(id=data["video_id"])
            plugin_manager = PluginManager()

            result = plugin_manager(
                data["plugin"],
                user=request.user,
                video=video_db,
                run_async=True,
                parameters=parameters,
            )

            if not result:
                return JsonResponse(
                    {"status": "error", "type": "plugin_not_started"},
                    status=500,
                )

            return JsonResponse({"status": "ok"})

        except serializers.ValidationError as e:
            return JsonResponse(
                {"status": "error", "type": "validation_error", "errors": e.detail},
                status=400,
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "type": "wrong_request_body"},
                status=400,
            )
        except Exception:
            logger.exception("Failed to create new plugin run")
            return JsonResponse({"status": "error"}, status=500)


class PluginRunDelete(View):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                logger.error("PluginRunNew::not_authenticated")
                return JsonResponse({"status": "error"})

            if request.method != "POST":
                logger.error("PluginRunNew::wrong_method")
                return JsonResponse({"status": "error"})

            try:
                body = request.body.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                body = request.body

            try:
                data = json.loads(body)
            except Exception as e:
                return JsonResponse({"status": "error"})

            if "plugin_list" not in data:
                return JsonResponse(
                    {"status": "error", "type": "missing_values_plugin_list"}
                )

            plugin_list = data.get("plugin_list")

            if list(plugin_list)[0] == 'all':
                response, _ = PluginRun.objects.filter(video__owner=request.user).delete()
            else:
                response, _ = PluginRun.objects.filter(
                    id__in=plugin_list,
                    video__owner=request.user,
                ).delete()

            return JsonResponse({"status": "ok", "deleted_items": response})
        except Exception:
            logger.exception("Failed to delete PluginRun")
            return JsonResponse({"status": "error"})


class PluginRunList(View):
    def get(self, request):
        start = time.time()
        if not request.user.is_authenticated:
            logger.error("PluginRunNew::not_authenticated")
            return JsonResponse({"status": "error"})

        plugin_manager = PluginManager()
        try:
            can_see_all = request.user.role in ("admin", "researcher")
            video_id = request.GET.get("video_id")
            if video_id:
                if can_see_all:
                    analyses = PluginRun.objects.filter(video__id=video_id)
                else:
                    analyses = PluginRun.objects.filter(video__id=video_id, video__owner=request.user)
            else:
                analyses = PluginRun.objects.filter(video__owner=request.user)
            add_results = request.GET.get("add_results")

            analyses = analyses.prefetch_related("video")

            end = time.time()
            logger.debug(f"Listing plugin before entry creation took {end - start}s")
            if add_results:
                entries = []
                for x in analyses:
                    results = plugin_manager.get_results(x)
                    if results:
                        entries.append({**x.to_dict(), "results": results})
                    else:
                        entries.append({**x.to_dict()})
            else:
                entries = [x.to_dict() for x in analyses]

            end = time.time()
            logger.debug(f"Listing plugin runs took {end - start}s")
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception('Failed to list plugin runs')
            return JsonResponse({"status": "error"})
