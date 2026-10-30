import json
import logging

import numpy as np
from django.views import View
from django.http import JsonResponse

from backend.models import Video
from backend.models import CalibrationAssets
from backend.models import PluginRun
from backend.utils.pitch import normalize_sport, object_pitch_positions, pitch_markings
from backend.utils.projection import is_calibrated, pitch_to_video, project_polylines, to_json_points, video_to_pitch
from backend.permissions import writable
from backend.utils.api import ApiView


logger = logging.getLogger(__name__)


class CalibrationAssetsCreate(ApiView):
    def post(self, request):
        data = request.data
        if "name" not in data:
            return JsonResponse({"status": "error", "type": "missing_values"})
        try: # read from db on existing entry
            query_args = {"name": data.get("name"), "owner": request.user}
            if "video_id" in data:
                query_args["video__id"] = data.get("video_id")

            data_db = CalibrationAssets.objects.get(**query_args)
                
        except CalibrationAssets.DoesNotExist:
            create_args = {
                "name": data.get("name"),
                "sport": data.get("sport"),
                "object_type": data.get("object_type"),
                "owner": request.user
            }
            if "video_id" in data:
                try:
                    video_db = writable(Video, request.user).get(id=data.get("video_id"))
                except Video.DoesNotExist:
                    return JsonResponse({"status": "error", "type": "not_exist"})
                create_args["video"] = video_db

            # create new entry
            data_db = CalibrationAssets.objects.create(**create_args)
            # create marker data points if provided
            if "object_data" in data:
                for obj in data.get("object_data"):
                    data_db.object_data.create(
                        name=obj.get("name"),
                        active=obj.get("active"),
                        comp_area_coords_rel=obj.get("compAreaCoordsRel"),
                        video_coords_rel=obj.get("videoCoordsRel")
                    )

        return JsonResponse({"status": "ok", "entry": data_db.to_dict()})


class CalibrationAssetsChange(ApiView):
    def post(self, request):
        data = request.data
        if "name" not in data:
            return JsonResponse({"status": "error", "type": "missing_values"})
        try:
            calibration_assets = writable(CalibrationAssets, request.user).get(id=data.get("id"))
            if "name" in data:
                calibration_assets.name = data.get("name")
            if "sport" in data:
                calibration_assets.sport = data.get("sport")
            if "object_type" in data:
                calibration_assets.object_type = data.get("object_type")
            if "object_data" in data:
                # clear existing marker data
                calibration_assets.object_data.all().delete()
                # create new marker data points
                for obj in data.get("object_data"):
                    calibration_assets.object_data.create(
                        name=obj.get("name"),
                        active=obj.get("active"),
                        comp_area_coords_rel=obj.get("compAreaCoordsRel"),
                        video_coords_rel=obj.get("videoCoordsRel")
                    )
                # the marker set changed, so any previously computed
                # homography no longer corresponds to it -- invalidate the
                # DLT / lens solver run and force a rerun
                PluginRun.objects.filter(
                    type__in=["calibration_static_dlt", "calibration_lens_solve"],
                    calibration_asset=calibration_assets,
                ).delete()
            calibration_assets.save()

            return JsonResponse({"status": "ok", "entry": calibration_assets.to_dict()})

        except CalibrationAssets.DoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception(f'Failed to {__class__.__name__}')
            return JsonResponse({"status": "error"})


class CalibrationAssetsDelete(ApiView):
    def post(self, request):
        data = request.data
        try:
            calibration_assets = writable(CalibrationAssets, request.user).get(id=data.get("id"))
            # object_data is stored on the asset and goes with it
            calibration_assets.delete()
            return JsonResponse({"status": "ok"})
        except CalibrationAssets.DoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})   
        except Exception:
            logger.exception(f'Failed to {__class__.__name__}')
            return JsonResponse({"status": "error"})


class CalibrationAssetsList(ApiView):
    def get(self, request):
        try:

            query_args = {}
            query_args["owner"] = request.user

            if "video_id" in request.GET:
                query_args["video__id"] = request.GET.get("video_id")
            query_results = CalibrationAssets.objects.filter(**query_args)

            entries = []
            for calibration_assets in query_results:
                entries.append(calibration_assets.to_dict())
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception('Failed to list all available calibration assets')
            return JsonResponse({"status": "error"})


def _calibration_context(calibration_assets):
    """sport, pitch size and lens of a calibration asset's video, as the DLT task uses them."""
    video = calibration_assets.video
    sport = normalize_sport(calibration_assets.sport, video.sport if video else None)
    field_length = (video.field_length if video else None) or 105.0
    field_width = (video.field_width if video else None) or 68.0
    return sport, field_length, field_width


def _clicked_points(calibration_assets):
    """All clicked video points of an asset (relative), which lie on the ground in front of the camera."""
    return [
        [p["x"], p["y"]]
        for obj in calibration_assets.object_data.all()
        for p in (obj.video_coords_rel or [])
        if p.get("x") is not None and p.get("y") is not None
    ]


class CalibrationAssetsOverlay(ApiView):
    """What a calibration asset's homography and lens put into the video (?id=), for the frontend to draw:

    - "markings": the pitch lines and circles, as polylines in relative video coordinates, split where the camera
      can't see them;
    - "objects": per calibration object, its pitch position (the metric model's for known markers, as the DLT
      fit uses it) projected into the video, next to where it was clicked ([x, y] or null per point).
    """
    def get(self, request):
        try:
            calibration_assets = CalibrationAssets.objects.get(id=request.GET.get("id"), owner=request.user)
            H, lens = calibration_assets.homography_matrix, calibration_assets.lens_intrinsics
            if not is_calibrated(H):
                return JsonResponse({"status": "ok", "calibrated": False, "markings": [], "objects": []})
            sport, field_length, field_width = _calibration_context(calibration_assets)
            clicks = _clicked_points(calibration_assets)
            markings = project_polylines(pitch_markings(sport, field_length, field_width), H, lens, clicks)
            objects = []
            for obj in calibration_assets.object_data.all():
                _, positions = object_pitch_positions(
                    sport, calibration_assets.object_type, obj.name, obj.comp_area_coords_rel or [],
                    field_length, field_width,
                )
                video = pitch_to_video(positions, H, lens, clicks) if positions else np.empty((0, 2))
                objects.append({"id": obj.id.hex, "name": obj.name, "points": to_json_points(video)})
            return JsonResponse({"status": "ok", "calibrated": True, "markings": markings, "objects": objects})
        except (CalibrationAssets.DoesNotExist, ValueError):
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception(f'Failed to {__class__.__name__}')
            return JsonResponse({"status": "error"})


class CalibrationAssetsProject(ApiView):
    """Points projected through a calibration asset's homography and lens: {"id", "points": [[x, y], ...],
    "direction": "video_to_pitch" (default) | "pitch_to_video"}, relative coordinates both ways. Returns
    {"points": [[x, y] | null, ...]}, null where a point can't be mapped."""
    def post(self, request):
        data = request.data
        try:
            calibration_assets = CalibrationAssets.objects.get(id=data.get("id"), owner=request.user)
        except (CalibrationAssets.DoesNotExist, ValueError):
            return JsonResponse({"status": "error", "type": "not_exist"})
        H, lens = calibration_assets.homography_matrix, calibration_assets.lens_intrinsics
        if not is_calibrated(H):
            return JsonResponse({"status": "error", "type": "not_calibrated"})
        points = np.asarray(data.get("points") or [], dtype=np.float64).reshape(-1, 2)
        direction = data.get("direction", "video_to_pitch")
        if direction == "video_to_pitch":
            projected = video_to_pitch(points, H, lens)
        elif direction == "pitch_to_video":
            projected = pitch_to_video(points, H, lens, _clicked_points(calibration_assets))
        else:
            return JsonResponse({"status": "error", "type": "wrong_direction"})
        return JsonResponse({"status": "ok", "points": to_json_points(projected)})
