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
    media_url_to_video,
    media_dir_to_video,
)
from backend.models import TrackingData

from django.views import View
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class TrackingDataUpload(View):
    
    # TODO: What is this for?
    # def submit_analyse(self, plugins, **kwargs):
    #     plugin_manager = PluginManager()
    #     for plugin in plugins:
    #         plugin_manager(plugin, **kwargs)

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
            tracking_data_id_uuid = uuid.uuid4()
            tracking_data_id = tracking_data_id_uuid.hex
            if "file" in request.FILES:
                output_dir = media_dir_to_video(tracking_data_id)  # TODO: what is this for?

                download_result = download_file(
                    output_dir=output_dir,
                    output_name=tracking_data_id,
                    file=request.FILES["file"],
                    max_size=request.user.max_video_size,
                    extensions=(".csv", ".xml"),  # TODO: adjust if other formats are needed
                )

                if download_result["status"] != "ok":
                    logger.error("TrackingDataUpload::failed")
                    return JsonResponse(download_result, status=500)

                path = Path(request.FILES["file"].name)
                ext = "".join(path.suffixes)

                # TODO: check which meta-information is needed
                # format: ['kinexon', 'dfl', ... ] -> 
                meta = {  
                    "name": request.POST.get("title"),
                    "ext": ext,
                    "format": "kinexon"  # TODO: obtain automatically from meta data...
                }
                tracking_data_db, created = TrackingData.objects.get_or_create(
                    name=meta["name"],
                    id=tracking_data_id_uuid,
                    file=tracking_data_id_uuid,
                    ext=meta["ext"],

                    owner=request.user,
                )
                if not created:
                    logger.error("VideoUpload::database_create_failed")
                    return JsonResponse(
                        {"status": "error", "type": "database_error"}, status=500
                    )

                tracking_data_id_hex = tracking_data_db.id.hex if not tracking_data_db.file.hex else tracking_data_db.id.hex
                return JsonResponse(
                    {
                        "status": "ok",
                        "entries": [
                            {
                                "id": tracking_data_id,
                                **tracking_data_db.to_dict(),
                                "url": media_url_to_video(tracking_data_id_hex, meta["ext"]),
                            }
                        ],
                    }
                )

            return JsonResponse({"status": "error"}, status=500)

        except Exception:
            logger.exception("Video upload by user failed")
            return JsonResponse({"status": "error"}, status=500)