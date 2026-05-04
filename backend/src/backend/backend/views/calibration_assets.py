import json
import logging
from django.views import View
from django.http import JsonResponse

from backend.models import Video
from backend.models import CalibrationAssets
from backend.utils.decode_auth import decode_and_authenticate


logger = logging.getLogger(__name__)


class CalibrationAssetsCreate(View):
    @decode_and_authenticate(require_name=True)
    def post(self, request, data): # data is passed from the decorator
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
                    video_db = Video.objects.get(id=data.get("video_id"))
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


class CalibrationAssetsChange(View):
    @decode_and_authenticate(require_name=True)
    def post(self, request, data):
        try:
            calibration_assets = CalibrationAssets.objects.get(id=data.get("id"))
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
            if "object_data" in data:
                for obj in data.get("object_data"):
                    obj.delete()
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
