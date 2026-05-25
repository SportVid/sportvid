import re
import json
import uuid
import logging
import tempfile
import tempfile
import time
from django.http import JsonResponse
from django.views import View
from rest_framework.exceptions import ValidationError as DRFValidationError

from backend.models import Video, PluginRun
from backend.plugin_manager import PluginManager
from backend.utils import download_url, download_file, media_url_to_file

logger = logging.getLogger(__name__)


class PluginRunNew(View):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                logger.error("PluginRunNew::not_authenticated")
                return JsonResponse({"status": "error"})

            output_dir = tempfile.mkdtemp(dir="/tmp")

            try:
                raw_parameters = request.POST.get("parameters", "[]")
                raw_parameters = json.loads(raw_parameters)
            except json.JSONDecodeError:
                return JsonResponse(
                    {"status": "error", "type": "wrong_request_body", "errors": {"parameters": ["Invalid JSON."]}},
                    status=400,
                )

            plugin = request.POST.get("plugin")
            if not plugin:
                return JsonResponse(
                    {"status": "error", "type": "missing_values", "errors": {"plugin": ["This field is required."]}},
                    status=400,
                )

            video_id = request.POST.get("video_id")
            if not video_id:
                return JsonResponse(
                    {"status": "error", "type": "missing_values", "errors": {"video_id": ["This field is required."]}},
                    status=400,
                )

            if not isinstance(raw_parameters, list):
                return JsonResponse(
                    {"status": "error", "type": "wrong_request_body", "errors": {"parameters": ["Must be a list."]}},
                    status=400,
                )

            plugin_manager = PluginManager()

            if plugin not in plugin_manager:
                logger.error("PluginRunNew::unknown_plugin %s", plugin)
                return JsonResponse({"status": "error", "type": "not_exist"}, status=404)

            try:
                video_db = Video.objects.get(id=video_id)
            except Video.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "type": "not_exist", "errors": {"video_id": ["Video does not exist."]}},
                    status=404,
                )

            serializer_cls = plugin_manager.get_serializer(plugin)
            if serializer_cls is None:
                logger.error("PluginRunNew::missing_serializer %s", plugin)
                return JsonResponse(
                    {
                        "status": "error",
                        "type": "server_error",
                        "errors": {"plugin": [f"No serializer registered for plugin '{plugin}'."]},
                    },
                    status=500,
                )

            normalized_parameters = {}

            for parameter in raw_parameters:
                if not isinstance(parameter, dict):
                    return JsonResponse(
                        {
                            "status": "error",
                            "type": "wrong_request_body",
                            "errors": {"parameters": ["Each parameter must be an object."]},
                        },
                        status=400,
                    )

                name = parameter.get("name")
                if not name:
                    return JsonResponse(
                        {
                            "status": "error",
                            "type": "wrong_request_body",
                            "errors": {"parameters": ["Each parameter needs a name."]},
                        },
                        status=400,
                    )

                if "value" not in parameter:
                    return JsonResponse(
                        {
                            "status": "error",
                            "type": "wrong_request_body",
                            "errors": {name: ["Missing 'value'."]},
                        },
                        status=400,
                    )

                normalized_parameters[name] = parameter["value"]

            # ------------> file upload handling
            for key, uploaded_file in request.FILES.items():
                match = re.match(r"^file_(.*?)$", key)
                if not match:
                    continue

                parameter_name = match.group(1)
                data_id_uuid = uuid.uuid4().hex

                download_result = download_file(
                    output_dir=output_dir,
                    output_name=data_id_uuid,
                    file=uploaded_file,
                    max_size=11 * 1024 * 1024 * 1024,
                )

                if download_result.get("status") != "ok":
                    return JsonResponse(
                        {
                            "status": "error",
                            "type": "file_upload_failed",
                            "errors": {parameter_name: ["Could not store uploaded file."]},
                        },
                        status=400,
                    )

                normalized_parameters[parameter_name] = download_result.get("path")

            # ------------> DRF serialization
            serializer = serializer_cls(data=normalized_parameters)
            try:
                serializer.is_valid(raise_exception=True)
            except DRFValidationError as exc:
                return JsonResponse(
                    {
                        "status": "error",
                        "type": "validation_error",
                        "errors": exc.detail,
                    },
                    status=400,
                )

            validated_parameters = serializer.validated_data
            
            result = plugin_manager.run(
                plugin,
                user=request.user,
                video=video_db,
                run_async=True,
                parameters=validated_parameters,
            )

            if result:
                return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "error", "type": "plugin_not_started"}, status=500)
        
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
            video_id = request.GET.get("video_id")
            if video_id:
                analyses = PluginRun.objects.filter(
                    video__id=video_id, video__owner=request.user
                )
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
