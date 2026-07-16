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

from backend.models import Video, PluginRun, TrackingData
from backend.plugin_manager import PluginManager
from backend.utils import download_url, download_file, media_url_to_file


logger = logging.getLogger(__name__)


class PluginRunNew(View):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                logger.error("PluginRunNew::not_authenticated")
                return JsonResponse({"status": "error"})

            if request.method != "POST":
                logger.error("PluginRunNew::wrong_method")
                return JsonResponse({"status": "error"})

            output_dir = tempfile.mkdtemp(dir="/tmp")
            parameters = []
            for k, v in request.FILES.items():
                m = re.match(r"^file_(.*?)$", k)
                if m:
                    data_id_uuid = uuid.uuid4().hex
                    download_result = download_file(
                        output_dir=output_dir,
                        output_name=data_id_uuid,
                        file=v,
                        max_size=11 * 1024 * 1024 * 1024,
                    )
                    if download_result.get("status") == "ok":
                        parameters.append(
                            {
                                "name": m.group(1),
                                "value": download_result.get("origin"),
                                "path": download_result.get("path"),
                            }
                        )
            parameters.extend(json.loads(request.POST.get("parameters")))
            plugin = request.POST.get("plugin")
            if plugin is None:
                return JsonResponse({"status": "error", "type": "missing_values"})

            video_id = request.POST.get("video_id")
            if video_id is None:
                return JsonResponse({"status": "error", "type": "missing_values"})

            if not isinstance(parameters, list):
                return JsonResponse({"status": "error", "type": "wrong_request_body"})
            valid_parameters = []
            for parameter in parameters:
                if not isinstance(parameter, dict):
                    return JsonResponse(
                        {"status": "error", "type": "wrong_request_body"}
                    )

                if "name" not in parameter:
                    return JsonResponse(
                        {"status": "error", "type": "wrong_request_body"}
                    )

                if "value" not in parameter:
                    return JsonResponse(
                        {"status": "error", "type": "wrong_request_body"}
                    )
                if "path" in parameter:
                    valid_parameters.append(
                        {
                            "name": parameter.get("name"),
                            "value": parameter.get("value"),
                            "path": parameter.get("path"),
                        }
                    )

                else:
                    valid_parameters.append(
                        {"name": parameter.get("name"), "value": parameter.get("value")}
                    )

            plugin_manager = PluginManager()

            if plugin not in plugin_manager:
                logger.error(plugin)
                return JsonResponse({"status": "error", "type": "not_exist"})

            try:
                video_db = Video.objects.get(id=video_id)
            except Video.DoesNotExist:
                return JsonResponse({"status": "error", "type": "not_exist"})

            user_db = request.user
            
            result = plugin_manager(
                plugin,
                user=user_db,
                video=video_db,
                run_async=True,
                parameters=valid_parameters,
            )

            if result:
                return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "error", "type": "plugin_not_started"})
        except Exception:
            logger.exception("Failed to create new plugin run")
            return JsonResponse({"status": "error"})


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
                runs = PluginRun.objects.filter(video__owner=request.user)
            else:
                runs = PluginRun.objects.filter(
                    id__in=plugin_list,
                    video__owner=request.user,
                )

            # posdata_convert runs own the uploaded TrackingData they were
            # created from -- deleting the run should delete that file too,
            # so it doesn't keep showing up as available elsewhere. This
            # also cascades away any kpi_computation run derived from the
            # same file.
            tracking_data_ids = list(
                runs.filter(type="posdata_convert", tracking_data__isnull=False)
                .values_list("tracking_data_id", flat=True)
            )
            cascaded_deleted = 0
            if tracking_data_ids:
                tdata_qs = TrackingData.objects.filter(id__in=tracking_data_ids)
                total_size = sum(
                    t.file_size + (t.meta_file_size if t.meta_file else 0) for t in tdata_qs
                )
                cascaded_deleted, _ = tdata_qs.delete()
                if cascaded_deleted:
                    request.user.used_storage_size = max(
                        0, request.user.used_storage_size - total_size
                    )
                    request.user.save()

            response, _ = runs.delete()

            return JsonResponse({"status": "ok", "deleted_items": response + cascaded_deleted})
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
