import json
import logging
from functools import wraps

from django.views import View
from django.http import JsonResponse

from backend.models import PluginRunResult
from backend.utils.decode_auth import decode_and_authenticate

from data import DataManager

logger = logging.getLogger(__name__)


class BoundingBoxesChange(View):
    @decode_and_authenticate(require_name=False)
    def post(self, request, data):
        try:
            logging.error(data)
            bytetrack_result_id = data.get("bytetrack_run_id")
            bytetrack_prr_db = PluginRunResult.objects.get(
                id=bytetrack_result_id
            )
            current_ref_id = None
            if "ref_id" in data: current_ref_id = data.get("ref_id")
        
            new_ref_id = None; new_team_id = None
            if "new_ref_id" in data: new_ref_id = data.get("new_ref_id")  
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
            
            logging.error(f'{current_ref_id},{new_ref_id},{new_team_id},{update_all_ref_id},{update_all_team_id}')    

            manager = DataManager("/predictions/")     
            # TODO: what would be the most efficient way to update the old data 
            with manager.load(bytetrack_prr_db.data_id) as bboxes_data:
                # NOTE: returns bboxes_data as BboxesData List-Wrapper
                bbd_dict = bboxes_data.to_dict()
                for entry in bbd_dict:
                    if entry.get("ref_id") == current_ref_id:
                        logging.error(entry.get("ref_id"))
                
                logging.error(bboxes_data.to_dict())
                # access to unziped files
            
            # with data_manager.create_data(data_type):
            
            # data_manager.delete -> physical delete 
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