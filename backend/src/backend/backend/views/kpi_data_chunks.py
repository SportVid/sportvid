import os
import json
import logging
from django.views import View
from django.http import JsonResponse
from django.conf import settings

from backend.models import PluginRun, PluginRunResult, Video
from data import DataManager


logger = logging.getLogger(__name__)


"""
Module-level in-memory cache: result.id -> parsed data dict.
Avoids re-reading the JSON file on every chunk request.
"""
_kpi_data_cache = {}


class PluginRunResultKpiChunk(View):
    """
    Serves KPI data in paginated chunks.

    GET /plugin/run/result/kpi/chunk
        ?tracking_data_id=<hex>
        &video_id=<uuid>
        &offset=0
        &limit=5000

    Response:
        { status, frames: {timeMs: {playerId: {kpiName: val}}}, total, offset, limit }
        meta_data is included only when offset=0.
    """

    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "type": "not_authenticated"}, status=403
                )

            tracking_data_id = request.GET.get("tracking_data_id")
            video_id = request.GET.get("video_id")

            if not tracking_data_id or not video_id:
                return JsonResponse(
                    {"status": "error", "type": "missing_params"}, status=400
                )

            try:
                offset = max(0, int(request.GET.get("offset", 0)))
            except (ValueError, TypeError):
                offset = 0
            try:
                limit = min(10000, max(1, int(request.GET.get("limit", 5000))))
            except (ValueError, TypeError):
                limit = 5000
            try:
                video_db = Video.objects.get(id=video_id)
            except Video.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "type": "video_not_found"}, status=404
                )
            # find kpi_computation plugin runs for this video
            plugin_runs = PluginRun.objects.filter(
                video=video_db,
                type="kpi_computation",
                status="D",
            )

            data_manager = DataManager("/predictions/")

            for pr in plugin_runs:
                for result in PluginRunResult.objects.filter(
                    plugin_run=pr, type=PluginRunResult.TYPE_KPI
                ):
                    data = self._load_result_data(result, data_manager)
                    if data is None:
                        continue

                    if data.get("tracking_data_id") != tracking_data_id:
                        continue

                    kpis = data.get("kpis", {})
                    meta_data = data.get("meta_data", {})

                    sorted_keys = sorted(kpis.keys(), key=lambda k: int(k))
                    total = len(sorted_keys)
                    chunk_keys = sorted_keys[offset: offset + limit]
                    chunk_frames = {k: kpis[k] for k in chunk_keys}

                    response = {
                        "status": "ok",
                        "frames": chunk_frames,
                        "total": total,
                        "offset": offset,
                        "limit": limit,
                    }
                    if offset == 0:
                        response["meta_data"] = meta_data

                    return JsonResponse(response)

            return JsonResponse(
                {"status": "error", "type": "not_found"}, status=404
            )
        except Exception:
            logger.exception("PluginRunResultKpiChunk::failed")
            return JsonResponse({"status": "error"}, status=500)

    @staticmethod
    def _load_result_data(result, data_manager):
        """ Load result data, with an in-memory cache keyed by result.id. """
        result_id = str(result.id)

        if result_id in _kpi_data_cache:
            return _kpi_data_cache[result_id]

        data = None
        # try file cache first
        cache_path = os.path.join(
            settings.DATA_CACHE_ROOT, f"{result.id}.json"
        )
        try:
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    cached = json.load(f)
                data = cached.get("data", {})
        except Exception:
            pass
        # fallback to DataManager
        if data is None:
            try:
                data_obj = data_manager.load(result.data_id)
                if data_obj is None:
                    return None
                with data_obj:
                    data = data_obj.to_dict()
            except Exception:
                return None

        if data is not None:
            _kpi_data_cache[result_id] = data

        return data
