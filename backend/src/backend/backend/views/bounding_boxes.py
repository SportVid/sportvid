import json
import logging
from functools import wraps

from django.db import transaction
from django.views import View
from django.http import JsonResponse

from backend.models import PluginRunResult
from backend.utils.decode_auth import decode_and_authenticate

from data import DataManager, BboxesData, BboxData

logger = logging.getLogger(__name__)


class BoundingBoxesChange(View):
    @decode_and_authenticate(require_name=False)
    def post(self, request, data):
        try:
            bytetrack_result_id = data.get("bytetrack_run_id")
            current_ref_id = None
            if "ref_id" in data: current_ref_id = int(data.get("ref_id"))
        
            new_ref_id = None; new_team_id = None
            if "new_ref_id" in data: new_ref_id = int(data.get("new_ref_id"))
            if "new_team_id" in data: new_team_id = data.get("new_team_id")
            
            if current_ref_id is None or (new_ref_id is None and new_team_id is None):
                return JsonResponse({"status": "error", "type": "missing_args"})
 
            update_all_ref_id = False; update_all_team_id = False
            if "update_all_ref_id" in data:
                if data.get("update_all_ref_id") in ['true', 'True']:
                    update_all_ref_id = True
            if "update_all_team_id" in data:
                if data.get("update_all_team_id") in ['true', 'True']:
                    update_all_team_id = True   
  
            with transaction.atomic():
                bytetrack_prr_db = PluginRunResult.objects.get_or_create(
                    plugin_run_id=bytetrack_result_id
                )
                logging.error(bytetrack_prr_db[0].data_id)
                logging.error(f'{current_ref_id},{new_ref_id},{new_team_id},{update_all_ref_id},{update_all_team_id}')    

                manager = DataManager("/predictions/")
                # manipulate unzipped files and create an altered 'BBoxesData' object
                with manager.load(bytetrack_prr_db[0].data_id) as bboxes_data:
                    bbd = bboxes_data.to_dict()
                    bbd_data = bbd["bboxes"]
                    with manager.create_data("BboxesData") as altered_bbx:
                        for entry in bbd_data:
                            if entry.get("ref_id") == current_ref_id:
                                entry["ref_id"] = new_ref_id
                            bbox = BboxData(**entry)
                            altered_bbx.bboxes.append(bbox)
                logging.error(altered_bbx.id)
                
                # remove old data from the fs
                manager.delete(bytetrack_prr_db.data_id)
                # change "data_id" reference to the id of the altered bbox data
                bytetrack_prr_db.update({"data_id": altered_bbx.id})
                
                logging.error(bytetrack_prr_db.data_id)

            return JsonResponse({"status": "ok", "entry": altered_bbx.to_dict()})
        except Exception:
            logger.exception('Failed to edit bounding box(es)')
            return JsonResponse({"status": "error"})

 
class BoundingBoxesDelete(View):
    @decode_and_authenticate(require_name=True)
    def post(self, request, data):
        try:
            logging.error(data)
        except Exception:
            logger.exception('Failed to delete bounding box(es)')
            return JsonResponse({"status": "error"})