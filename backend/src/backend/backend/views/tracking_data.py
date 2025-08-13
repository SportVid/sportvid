import os
import shutil
import sys
import json
import uuid
import logging
import traceback
import tempfile
import logging
from pathlib import Path

from urllib.parse import urlparse
from backend.plugin_manager import PluginManager
from backend.utils import (
    download_file,
    media_url_to_file,
    media_dir_to_file,
)
from backend.models import TrackingData

from django.views import View
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class TrackingDataUpload(View):
    
    def submit_analyse(self, plugins, **kwargs):
        plugin_manager = PluginManager()
        for plugin in plugins:
            plugin_manager(plugin, **kwargs)

    def post(self, request):
        try:
            if not request.user.is_authenticated:
                logger.error("TrackingDataUpload::not_authenticated")
                return JsonResponse(
                    {"status": "error", "type": "not_authenticated"}, status=500
                )

            if request.method != "POST":
                logger.error("TrackingDataUpload::wrong_method")
                return JsonResponse(
                    {"status": "error", "type": "database_error"}, status=500
                )

            logger.error(request.POST.fps)
            
            tracking_data_id_uuid = uuid.uuid4()
            tracking_data_id = tracking_data_id_uuid.hex
            
            if "file" in request.FILES:
                output_dir = media_dir_to_file(tracking_data_id)

                download_result = download_file(
                    output_dir=output_dir,
                    output_name=tracking_data_id,
                    file=request.FILES["file"],
                    max_size=request.user.max_file_size,
                    extensions=(".csv", ".xml"),
                )

                if download_result["status"] != "ok":
                    logger.error("TrackingDataUpload::failed")
                    return JsonResponse(download_result, status=500)
            
                meta_data_id_uuid = uuid.uuid4()
                meta_data_id = meta_data_id_uuid.hex
                
                if "meta_data" in request.FILES:
                    output_dir = media_dir_to_file(meta_data_id)
                    
                    download_result = download_file(
                        output_dir=output_dir,
                        output_name=meta_data_id,
                        file=request.FILES["meta_data"],
                        max_size=request.user.max_file_size,
                        extensions=(".csv", ".xml"),
                    )
                    
                    if download_result["status"] != "ok":
                        logger.error("TrackingDataUpload::failed")
                        return JsonResponse(download_result, status=500)

                td_path = Path(request.FILES["file"].name)
                td_ext = "".join(td_path.suffixes)
                
                meta_path = Path(request.FILES["meta_data"].name)
                meta_ext = "".join(meta_path.suffixes)
                
                meta = {
                    "name": request.POST.get("title"),
                    "ext": td_ext,
                    "meta_ext": meta_ext,
                    "format": request.POST.get("format")
                }
                tracking_data_db, created = TrackingData.objects.get_or_create(
                    name=meta["name"],
                    id=tracking_data_id_uuid,
                    file=tracking_data_id_uuid,
                    meta_file=meta_data_id_uuid,
                    ext=meta["ext"],
                    meta_ext=meta["meta_ext"],
                    file_type=meta["format"],  # NOTE: specifies the format -> ['kinexon', 'dfl', ... ]
                    owner=request.user
                )
                if not created:
                    logger.error("TrackingDataUpload::database_create_failed")
                    return JsonResponse(
                        {"status": "error", "type": "database_error"}, status=500
                    )
                
                # TODO: submit conversion plugin on upload of tracking data
                # since the data can come from a range of different providers
                # we have to pass the right arguments to the conversion plugin
                # Additionally, tracking data may contain a meta file.
                self.submit_analyse(
                    plugins=["posdata_convert"], 
                    tracking_data=tracking_data_db,
                    user=request.user,
                    parameters={
                        "format": meta["format"],
                        "fps": request.POST.fps,
                        "delimiter": request.POST.delimiter if request.POST.delimiter else ';'
                    }
                )

                tracking_data_id_hex = tracking_data_db.id.hex if not tracking_data_db.file.hex else tracking_data_db.id.hex
                meta_data_id_hex = tracking_data_db.meta_file.hex
                return JsonResponse(
                    {
                        "status": "ok",
                        "entries": [
                            {
                                "id": tracking_data_id,
                                **tracking_data_db.to_dict(),
                                "url": media_url_to_file(tracking_data_id_hex, meta["ext"]),
                                "meta_url": media_url_to_file(meta_data_id_hex, meta["meta_ext"])
                            }
                        ],
                    }
                )
            return JsonResponse({"status": "error"}, status=500)

        except Exception:
            logger.exception("TrackingData upload by user failed")
            return JsonResponse({"status": "error"}, status=500)


class TrackingDataList(View):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=500)
            entries = []
            for tdata in TrackingData.objects.filter(owner=request.user):
                entries.append(tdata.to_dict())
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
            count, _ = TrackingData.objects.filter(
                id=data.get("id"), owner=request.user
            ).delete()
            if count:
                return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "error"}, status=500)
        except Exception:
            logger.exception("Failed to delete tracking data")
            return JsonResponse({"status": "error"}, status=500)