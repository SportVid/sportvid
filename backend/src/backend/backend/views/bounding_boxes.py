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
            bbox_id = data.get("bbox_id")
            bytetrack_result_id = data.get("bytetrack_run_id")
            current_ref_id = None
            if "ref_id" in data: current_ref_id = int(data.get("ref_id"))
        
            new_ref_id = None; new_team_id = None
            if "new_ref_id" in data: new_ref_id = int(data.get("new_ref_id"))
            if "new_team_id" in data: new_team_id = data.get("new_team_id")
            
            if bbox_id is None or ( 
                current_ref_id is None) or (
                    new_ref_id is None and new_team_id is None):
                return JsonResponse({"status": "error", "type": "missing_args"})
 
            update_all_ref_id = False; update_all_team_id = False
            if "update_all_ref_id" in data:
                if data.get("update_all_ref_id") in ['true', 'True']:
                    update_all_ref_id = True
            if "update_all_team_id" in data:
                if data.get("update_all_team_id") in ['true', 'True']:
                    update_all_team_id = True   
  
            # Get the DB record and store the old data_id before changing anything.
            bytetrack_prr_db = PluginRunResult.objects.get(
                plugin_run_id=bytetrack_result_id
            )
            old_data_id = bytetrack_prr_db.data_id
            logging.info(f"Preparing to update data for {bytetrack_prr_db.id}... old data_id: {old_data_id}")

            manager = DataManager("/predictions/")
            altered_bbx = None

            # Prepare the new data on the file system
            # If this fails, we haven't touched the DB and can exit safely
            # TODO: find a more efficient solution; right now recreates data entry by entry...
            with manager.load(old_data_id) as bboxes_data:
                bbd = bboxes_data.to_dict()
                bbd_data = bbd["bboxes"]
                with manager.create_data("BboxesData") as altered_bbx:
                    if update_all_ref_id:
                        # --- bulk delete; iterate each entry O(n)
                        for entry in bbd_data:
                            if entry.get("ref_id") == current_ref_id:
                                entry["ref_id"] = new_ref_id
                                if update_all_team_id:
                                    entry["team_id"] = new_team_id
                            bbox = BboxData(**entry)
                            altered_bbx.bboxes.append(bbox)
                    else:
                        # --- single delete; O(n)
                        for entry in bbd_data:
                            if entry.get("id") == bbox_id:
                                entry["ref_id"] = new_ref_id
                                if new_team_id: entry["team_id"] = new_team_id
                            bbox = BboxData(**entry)
                            altered_bbx.bboxes.append(bbox)   

            logging.info(f"Successfully created new temporary data with id: {altered_bbx.id}")

            # Perform the database switch inside a transaction.
            with transaction.atomic():
                # Re-fetch the object inside the transaction to ensure it's not stale
                # and to lock the row (if using select_for_update).
                prr_to_update = PluginRunResult.objects.get(pk=bytetrack_prr_db.pk)
                prr_to_update.data_id = altered_bbx.id
                prr_to_update.save()

            # If the transaction was successful, clean up the old file
            manager.delete(old_data_id)
            logging.info(f"Successfully updated DB and deleted old data {old_data_id}.")
            return JsonResponse({"status": "ok", "entry": altered_bbx.to_dict()})
        except Exception as e:
            logging.error(f"Failed to update bounding box data: {e}", exc_info=True)
            # If anything failed, delete the newly created (now orphaned) file
            if altered_bbx and altered_bbx.id:
                logging.warning(f"Rolling back: deleting temporary data {altered_bbx.id}")
                manager.delete(altered_bbx.id)

            # Re-raise the exception so Django's error handling can take over
            # raise
            return JsonResponse(
                {'status': 'error', 
                 'message': ''
                }, 
                status=500
            )

 
class BoundingBoxesDelete(View):
    @decode_and_authenticate(require_name=True)
    def post(self, request, data):
        try:
            bbox_id = data.get("bbox_id")
            bytetrack_result_id = data.get("bytetrack_run_id")
            ref_id_to_delete = None
            if "ref_id" in data: ref_id_to_delete = int(data.get("ref_id"))
            if ref_id_to_delete is None:
                return JsonResponse({"status": "error", "type": "missing_args"})
 
            delete_all_ref_id = False
            if "delete_all_ref_id" in data:
                if data.get("delete_all_ref_id") in ['true', 'True']:
                    delete_all_ref_id = True
  
            # Get the DB record and store the old data_id before changing anything.
            bytetrack_prr_db = PluginRunResult.objects.get(
                plugin_run_id=bytetrack_result_id
            )
            old_data_id = bytetrack_prr_db.data_id
            logging.info(f"Preparing to delete data for {bytetrack_prr_db.id}... old data_id: {old_data_id}")

            manager = DataManager("/predictions/")
            altered_bbx = None

            # Prepare the new data on the file system
            # If this fails, we haven't touched the DB and can exit safely
            # TODO: find a more efficient solution; right now recreates data entry by entry...
            with manager.load(old_data_id) as bboxes_data:
                bbd = bboxes_data.to_dict()
                bbd_data = bbd["bboxes"]
                with manager.create_data("BboxesData") as altered_bbx:
                    if delete_all_ref_id:
                        # --- bulk delete; iterate each entry O(n)
                        for entry in bbd_data:
                            if entry.get("ref_id") == ref_id_to_delete:
                                continue
                            bbox = BboxData(**entry)
                            altered_bbx.bboxes.append(bbox)
                    else:
                        # --- single edit; O(n)
                        for entry in bbd_data:
                            if entry.get("id") == bbox_id:
                                continue
                            bbox = BboxData(**entry)
                            altered_bbx.bboxes.append(bbox) 
            logging.info(f"Successfully created new temporary data with id: {altered_bbx.id}")

            # Perform the database switch inside a transaction.
            with transaction.atomic():
                # Re-fetch the object inside the transaction to ensure it's not stale
                # and to lock the row (if using select_for_update).
                prr_to_update = PluginRunResult.objects.get(pk=bytetrack_prr_db.pk)
                prr_to_update.data_id = altered_bbx.id
                prr_to_update.save()

            # If the transaction was successful, clean up the old file
            manager.delete(old_data_id)
            logging.info(f"Successfully updated DB and deleted old data {old_data_id}.")
            return JsonResponse({"status": "ok", "entry": altered_bbx.to_dict()})
        except Exception as e:
            logging.error(f"Failed to delete bounding box data: {e}", exc_info=True)
            # If anything failed, delete the newly created (now orphaned) file
            if altered_bbx and altered_bbx.id:
                logging.warning(f"Rolling back: deleting temporary data {altered_bbx.id}")
                manager.delete(altered_bbx.id)

            # Re-raise the exception so Django's error handling can take over
            # raise
            return JsonResponse(
                {'status': 'error', 
                 'message': ''
                }, 
                status=500
            )