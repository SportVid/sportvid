import json
import uuid
import logging
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from pathlib import Path

from backend.plugin_manager import PluginManager
from backend.utils import (
    download_file,
    media_url_to_file,
    media_dir_to_file,
)
from backend.models import TrackingData, Video


logger = logging.getLogger(__name__)


class TrackingDataUpload(View):
    
    def submit_analyse(self, plugins, **kwargs):
        plugin_manager = PluginManager()
        result = {"status": False}
        for plugin in plugins:
            result = plugin_manager(plugin, **kwargs)
        return result

    def post(self, request):
        try:
            if not request.user.is_authenticated:
                logger.error("TrackingDataUpload::not_authenticated")
                return JsonResponse(
                    {"status": "error", "type": "not_authenticated"}, status=500)

            if request.method != "POST":
                logger.error("TrackingDataUpload::wrong_method")
                return JsonResponse(
                    {"status": "error", "type": "database_error"}, status=500)
            
            tracking_data_id_uuid = uuid.uuid4()
            tracking_data_id = tracking_data_id_uuid.hex
            video_db = Video.objects.get(id=request.POST.get("video_id"))
            
            if "file" in request.FILES:
                output_dir = media_dir_to_file(tracking_data_id)

                download_result = download_file(
                    output_dir=output_dir,
                    output_name=tracking_data_id,
                    file=request.FILES["file"],
                    max_size=request.user.max_file_size,
                    extensions=(".csv", ".xml")
                )
                
                if download_result["status"] != "ok":
                    logger.error("TrackingDataUpload::failed")
                    return JsonResponse(download_result, status=500)
            
                td_path = Path(request.FILES["file"].name)
                td_ext = "".join(td_path.suffixes)

                db_params = {
                    "id": tracking_data_id_uuid,
                    "file": tracking_data_id_uuid,
                    "file_size": request.FILES["file"].size,
                    "name": request.POST.get("title"),
                    "ext": td_ext,
                    "file_type": request.POST.get("format"),
                    "owner": request.user,
                    "video": video_db,
                    "delimiter": request.POST.get("delimiter", ";"),
                }
            
                meta_ext = ""
                if "meta_data" in request.FILES:
                    meta_data_id_uuid = uuid.uuid4()
                    meta_data_id = meta_data_id_uuid.hex
                    
                    output_dir = media_dir_to_file(meta_data_id)
                    
                    download_result = download_file(
                        output_dir=output_dir,
                        output_name=meta_data_id,
                        file=request.FILES["meta_data"],
                        max_size=request.user.max_file_size,
                        extensions=(".csv", ".xml")
                    )
                    
                    if download_result["status"] != "ok":
                        logger.error("TrackingDataUpload::failed")
                        return JsonResponse(download_result, status=500)
                    
                    meta_path = Path(request.FILES["meta_data"].name)
                    meta_ext = meta_ext.join(meta_path.suffixes)
                    
                    db_params.update({"meta_file": meta_data_id_uuid, "meta_ext": meta_ext, "meta_file_size": request.FILES["meta_data"].size})
                else:
                    if request.POST.get("format") == 'dfl':  # meta_data file is mandatory for DFL data
                        logger.error("TrackingDataUpload::failed")
                        return JsonResponse(
                            {"status": "error"}, status=500)

                tracking_data_db, created = TrackingData.objects.get_or_create(**db_params)
                if not created:
                    logger.error("TrackingDataUpload::database_create_failed")
                    return JsonResponse(
                        {"status": "error", "type": "database_error"}, status=500)
                
                analyser_params = [
                    {"name": "tracking_data_id", "value": tracking_data_db.id.hex},
                    {"name": "format", "value": db_params["file_type"]}
                ]
                if request.POST.get("fps"):
                    analyser_params.append({"name": "fps", "value": request.POST.get("fps")})
                if request.POST.get("delimiter"):
                    analyser_params.append({"name": "delimiter", "value": request.POST.get("delimiter")})
                if request.POST.get("format") == "kinexon":
                    analyser_params.extend([
                        {"name": "field_length", "value": video_db.field_length},
                        {"name": "field_width", "value": video_db.field_width}
                    ])
                    if request.POST.get("team_id_ball"):
                        analyser_params.append({"name": "team_id_ball", "value": request.POST.get("team_id_ball")})
                    if request.POST.get("team_id_ref"):
                        analyser_params.append({"name": "team_id_ref", "value": request.POST.get("team_id_ref")})
  
                result = self.submit_analyse(
                    plugins=["posdata_convert"],
                    video=video_db,
                    user=request.user,
                    parameters=analyser_params
                )

                tracking_data_id_hex = tracking_data_db.id.hex if not tracking_data_db.file.hex else tracking_data_db.id.hex
                
                json_entries = [{
                    "id": tracking_data_id,
                    **tracking_data_db.to_dict(),
                    "url": media_url_to_file(tracking_data_id_hex, td_ext),
                }]
                
                if meta_ext != "":  # optional handling of meta data
                    meta_data_id_hex = tracking_data_db.meta_file.hex
                    json_entries[0].update({"meta_url": media_url_to_file(meta_data_id_hex, meta_ext)})

                if "file" in request.FILES:
                    request.user.used_storage_size += request.FILES["file"].size
                if "meta_data" in request.FILES:
                    request.user.used_storage_size += request.FILES["meta_data"].size
                request.user.save()
                
                return JsonResponse(
                    {
                        "status": "ok",
                        "entries": json_entries
                    }
                )
            return JsonResponse({"status": "error"}, status=500)

        except Exception:
            logger.exception("TrackingDataUpload::failed")
            return JsonResponse({"status": "error"}, status=500)


class TrackingDataList(View):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=500)
            can_see_all = request.user.role in ("admin", "researcher")
            video_id = request.GET.get("video_id")
            if video_id:
                if can_see_all:
                    queryset = TrackingData.objects.filter(video_id=video_id)
                else:
                    queryset = TrackingData.objects.filter(video_id=video_id, owner=request.user)
            else:
                queryset = TrackingData.objects.filter(owner=request.user)
            entries = [tdata.to_dict() for tdata in queryset]
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception as e:
            logger.exception("Error listing tracking data")
            return JsonResponse({"status": "error"}, status=500)


class TrackingDataGet(View):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=500)

            entries = []
            for tdata in TrackingData.objects.filter(id=request.GET.get("id"), owner=request.user):
                tracking_data_id_hex = tdata.id.hex if not tdata.file else tdata.file.hex
                entries.append(
                    {
                        **tdata.to_dict(),
                        "url": media_url_to_file(tracking_data_id_hex, tdata.ext),
                    }
                )
            if len(entries) != 1:
                return JsonResponse({"status": "error"}, status=500)
            return JsonResponse({"status": "ok", "entry": entries[0]})
        except Exception:
            logger.exception("Failed to get tracking data")
            return JsonResponse({"status": "error"}, status=500)


class TrackingDataRename(View):
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
                tracking_data_db = TrackingData.objects.get(id=data.get("id"))
            except TrackingData.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "type": "not_exist"}, status=500
                )

            tracking_data_db.name = data.get("name")
            tracking_data_db.save()
            return JsonResponse({"status": "ok", "entry": tracking_data_db.to_dict()})
        except Exception:
            logger.exception("Failed to rename tracking data")
            return JsonResponse({"status": "error"}, status=500)


class TrackingDataDelete(View):
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
            
            # TODO: delete for prod
            if data.get("id") == 'all': 
                all_tdata = TrackingData.objects.all()
                total_size = sum(
                    t.file_size + (t.meta_file_size if t.meta_file else 0) for t in all_tdata
                )
                count, _ = all_tdata.delete()
                if count:
                    request.user.used_storage_size = max(0, request.user.used_storage_size - total_size)
                    request.user.save()
                    return JsonResponse({"status": "ok"})
            else:
                tdata = TrackingData.objects.filter(id=data.get("id"), owner=request.user).first()
                file_size = tdata.file_size + (tdata.meta_file_size if tdata.meta_file else 0)
                count, _ = TrackingData.objects.filter(
                    id=data.get("id"), owner=request.user
                ).delete()
                if count:
                    request.user.used_storage_size = max(0, request.user.used_storage_size - file_size)
                    request.user.save()
                    return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "error"}, status=500)
        except Exception:
            logger.exception("Failed to delete tracking data")
            return JsonResponse({"status": "error"}, status=500)