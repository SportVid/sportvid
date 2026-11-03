import logging
import json
from django.views import View
from django.http import JsonResponse
from django.conf import settings

from backend.permissions import readable, writable
from backend.models import Video, VideoAnalysisState, Timeline, PluginRun
from backend.utils.api import ApiView


logger = logging.getLogger(__name__)


class VideoAnalysisStateGet(ApiView):
    legacy_errors = False  # already answered errors with error status codes

    def get(self, request):
        try:
            video_db = readable(Video, request.user).get(id=request.GET.get("video_id"))
        except Video.DoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"}, status=500)

        video_analysis_state_db, _ = VideoAnalysisState.objects.get_or_create(
            video=video_db
        )

        return JsonResponse(
            {"status": "ok", "entry": video_analysis_state_db.to_dict()}
        )


class VideoAnalysisStateSetSelectedShots(ApiView):
    legacy_errors = False  # already answered errors with error status codes

    def post(self, request):
        
        data = request.data

        if "video_id" not in data:
            return JsonResponse(
                {"status": "error", "type": "missing_values"}, status=500
            )

        if "timeline_id" not in data:
            return JsonResponse(
                {"status": "error", "type": "missing_values"}, status=500
            )

        if not writable(Video, request.user).filter(id=data["video_id"]).exists():
            return JsonResponse({"status": "error", "type": "not_exist"}, status=500)

        video_analysis_state_db, _ = VideoAnalysisState.objects.get_or_create(
            video_id=data["video_id"]
        )

        try:
            annotation_timeline_db = Timeline.objects.get(
                video__id=data["video_id"], id=data["timeline_id"]
            )
        except Timeline.DoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"}, status=500)

        video_analysis_state_db.selected_shots = annotation_timeline_db
        video_analysis_state_db.save()

        return JsonResponse({"status": "ok"})


class VideoAnalysisStateSetSelectedPlaceClustering(ApiView):
    legacy_errors = False  # already answered errors with error status codes

    def post(self, request):

        data = request.data

        if "video_id" not in data:
            return JsonResponse(
                {"status": "error", "type": "missing_values"}, status=500
            )

        if "plugin_run_id" not in data:
            return JsonResponse(
                {"status": "error", "type": "missing_values"}, status=500
            )

        if not writable(Video, request.user).filter(id=data["video_id"]).exists():
            return JsonResponse({"status": "error", "type": "not_exist"}, status=500)

        video_analysis_state_db, _ = VideoAnalysisState.objects.get_or_create(
            video_id=data["video_id"]
        )

        try:
            plugin_run_db = PluginRun.objects.get(
                video__id=data["video_id"],
                id=data["plugin_run_id"],
                type="place_clustering",
            )
        except PluginRun.DoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"}, status=500)

        video_analysis_state_db.selected_place_clustering = plugin_run_db
        video_analysis_state_db.save()

        return JsonResponse({"status": "ok"})


class VideoAnalysisStateSetSelectedFaceClustering(ApiView):
    legacy_errors = False  # already answered errors with error status codes

    def post(self, request):

        data = request.data

        if "video_id" not in data:
            return JsonResponse(
                {"status": "error", "type": "missing_values"}, status=500
            )

        if "plugin_run_id" not in data:
            return JsonResponse(
                {"status": "error", "type": "missing_values"}, status=500
            )

        if not writable(Video, request.user).filter(id=data["video_id"]).exists():
            return JsonResponse({"status": "error", "type": "not_exist"}, status=500)

        video_analysis_state_db, _ = VideoAnalysisState.objects.get_or_create(
            video_id=data["video_id"]
        )

        try:
            plugin_run_db = PluginRun.objects.get(
                video__id=data["video_id"],
                id=data["plugin_run_id"],
                type="face_clustering",
            )
        except PluginRun.DoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"}, status=500)

        video_analysis_state_db.selected_face_clustering = plugin_run_db
        video_analysis_state_db.save()

        return JsonResponse({"status": "ok"})
