import json
import logging
from functools import wraps

from django.views import View
from django.http import JsonResponse

from backend.models import Video
from backend.models import CalibrationAssets

logger = logging.getLogger(__name__)


def decode_and_authenticate(require_name=True):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            try:
                if not request.user.is_authenticated:
                    return JsonResponse({"status": "error", "type": "not_authenticated"})
                
                try:
                    body = request.body.decode("utf-8")
                except (UnicodeDecodeError, AttributeError):
                    body = request.body

                try:
                    data = json.loads(body)
                except Exception:
                    return JsonResponse({"status": "error", "type": "wrong_request_body"})

                if require_name and "name" not in data:
                    return JsonResponse({"status": "error", "type": "missing_values"})

                return view_func(self, request, data, *args, **kwargs)
            except Exception:
                logger.exception(f'Failed in {view_func.__name__}')
                return JsonResponse({"status": "error"})
        return wrapper
    return decorator


class CalibrationAssetsCreate(View):
    @decode_and_authenticate(require_name=True)
    def post(self, request, data): # data is passed from the decorator
        try: # read from db on existing entry
            query_args = {"name": data.get("name"), "owner": request.user}
            if "video_id" in data:
                query_args["video__id"] = data.get("video_id")

            data_db = CalibrationAssets.objects.get(**query_args)
                
        except CalibrationAssets.DoesNotExist:
            create_args = {"name": data.get("name"), "template": data.get("template"), "owner": request.user}
            if "video_id" in data:
                try:
                    video_db = Video.objects.get(id=data.get("video_id"))
                except Video.DoesNotExist:
                    return JsonResponse({"status": "error", "type": "not_exist"})
                create_args["video"] = video_db

            # create new entry
            data_db = CalibrationAssets.objects.create(**create_args)
            # Create marker data points if provided
            if "marker_data" in data:
                for marker in data.get("marker_data"):
                    data_db.marker_data.create(
                        name=marker.get("name"),
                        active=marker.get("active"),
                        compAreaCoord_x=marker["compAreaCoordsRel"]["x"],
                        compAreaCoord_y=marker["compAreaCoordsRel"]["y"],
                        compAreaCoord_z=marker["compAreaCoordsRel"]["z"] if "z" in marker["compAreaCoordsRel"] else 0.0,
                        videoCoord_x=marker["videoCoordsRel"]["x"],
                        videoCoord_y=marker["videoCoordsRel"]["y"],
                        videoCoord_z=marker["videoCoordsRel"]["z"] if "z" in marker["videoCoordsRel"] else 0.0,
                    )

        return JsonResponse({"status": "ok", "entry": data_db.to_dict()})

class CalibrationAssetsChange(View):
    @decode_and_authenticate(require_name=True)
    def post(self, request, data):
        try:
            calibration_assets = CalibrationAssets.objects.get(id=data.get("id"))
            if "name" in data:
                calibration_assets.name = data.get("name")
            if "template" in data:
                calibration_assets.template = data.get("template")
            if "marker_data" in data:
                # Clear existing marker data
                calibration_assets.marker_data.all().delete()
                # Create new marker data points
                for marker in data.get("marker_data"):
                    calibration_assets.marker_data.create(
                        name=marker.get("name"),
                        active=marker.get("active"),
                        compAreaCoord_x=marker["compAreaCoordsRel"]["x"],
                        compAreaCoord_y=marker["compAreaCoordsRel"]["y"],
                        compAreaCoord_z=marker["compAreaCoordsRel"]["z"] if "z" in marker["compAreaCoordsRel"] else 0.0,
                        videoCoord_x=marker["videoCoordsRel"]["x"],
                        videoCoord_y=marker["videoCoordsRel"]["y"],
                        videoCoord_z=marker["videoCoordsRel"]["z"] if "z" in marker["videoCoordsRel"] else 0.0,
                    )
            calibration_assets.save()

            return JsonResponse({"status": "ok", "entry": calibration_assets.to_dict()})

        except CalibrationAssets.DoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception(f'Failed to {__class__.__name__}')
            return JsonResponse({"status": "error"})

class CalibrationAssetsDelete(View):
    @decode_and_authenticate(require_name=False)
    def post(self, request, data):
        try:
            calibration_assets = CalibrationAssets.objects.get(id=data.get("id"))
            calibration_assets.delete()
            if "marker_data" in data:
                for marker in data.get("marker_data"):
                    marker.delete()
            return JsonResponse({"status": "ok"})
        except CalibrationAssets.DoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})   
        except Exception:
            logger.exception(f'Failed to {__class__.__name__}')
            return JsonResponse({"status": "error"})


class CalibrationAssetsList(View):
    def get(self, request):
        try:

            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"})

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
