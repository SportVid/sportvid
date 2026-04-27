import os
import json
import logging
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.views import View
from django.http import JsonResponse

from backend.models import PluginRunResult
from backend.utils.decode_auth import decode_and_authenticate

from data import (
    DataManager, 
    BboxesData, 
    BboxData
)

logger = logging.getLogger(__name__)


def _compute_meta_data(bbd_data):
    unique_player_ids = set()
    unique_team_ids = set()
    for frame_bboxes in bbd_data.values():
        for bbox in frame_bboxes:
            if len(bbox) > 1:
                unique_player_ids.add(bbox[0])
                unique_team_ids.add(bbox[1])
    team_id_meta = {}
    for idx, tid in enumerate(sorted(unique_team_ids)):
        name = chr(ord('A') + idx) if idx < 26 else str(tid)
        team_id_meta[tid] = {"id": tid, "name": name}
    player_id_meta = {}
    for pid in sorted(unique_player_ids):
        player_id_meta[pid] = {"id": pid, "name": str(pid), "number": pid}
    return json.dumps({"team_ids": team_id_meta, "player_ids": player_id_meta})


class BoundingBoxesChange(View):
    @decode_and_authenticate(require_name=False)
    def post(self, request, data):
        try:
            bbox_id = data.get("bbox_id")
            bytetrack_result_id = data.get("bytetrack_run_id")
            
            current_player_id = None; current_team_id = None 
            new_player_id = None; new_team_id = None
            update_all_player_id = False; update_all_team_id = False
            
            if "player_id" in data: current_player_id = int(data.get("player_id"))
            if "team_id" in data: current_team_id = int(data.get("team_id"))
            if "new_player_id" in data: new_player_id = int(data.get("new_player_id"))
            if "new_team_id" in data: new_team_id = int(data.get("new_team_id"))
            if "update_all_player_id" in data:
                if data.get("update_all_player_id") in ['true', 'True', True]:
                    update_all_player_id = True
            if "update_all_team_id" in data:
                if data.get("update_all_team_id") in ['true', 'True', True]:
                    update_all_team_id = True   
  
            # possible update ops.
            CH = None
            if not update_all_player_id and bbox_id: 
                CH='SINGLE_PLAYER_ID'
                if new_team_id and not update_all_team_id:
                    CH='SINGLE_PLAYERTEAM_ID'
            if update_all_player_id and current_player_id and new_player_id:
                CH='BULK_PLAYER_ID'
                if current_team_id and new_team_id:
                    CH='BULK_PLAYERTEAM_ID'
            if (current_team_id is not None and new_team_id is not None) and (
                update_all_team_id and not new_player_id): 
                CH='BULK_TEAM'

            if not CH: return JsonResponse({"status": "error", "type": "missing_args"})
            else: logging.info(f'running {CH} update op. on bbox data...')
  
            # get the DB record and store the old data_id before changing anything.
            bytetrack_prr_db = PluginRunResult.objects.get(
                plugin_run_id=bytetrack_result_id
            )
            old_data_id = bytetrack_prr_db.data_id
            logging.info(f"Preparing to update data for {bytetrack_prr_db.id}... old data_id: {old_data_id}")

            manager = DataManager("/predictions/")
            altered_bbx = None

            # prepare the new data on the file system
            # if this fails, we haven't touched the DB and can exit safely
            # NOTE: look for a more efficient solution; right now recreates data entry by entry...
            with manager.load(old_data_id) as bboxes_data:
                bbd = bboxes_data.to_dict()
                bbd_data = json.loads(bbd["bboxes"])
                with manager.create_data("BboxesData") as altered_bbx:
                    if not update_all_player_id and bbox_id:
                        # --- single edit (1 frame); O(n) at worse
                        frame_id = str(bbox_id.split("-", 1)[0])  # only iterate through lists that are related to the frame
                        for bbx in bbd_data[frame_id]:
                            # mutate list
                            if bbx[5] == bbox_id:
                                bbx[0] = new_player_id
                                bbx[5] = f"{frame_id}-{new_player_id}"
                                bbx[1] = new_team_id
                                break
                    if update_all_player_id and current_player_id and new_player_id:
                        # --- bulk edit (all frames); iterates each entry O(n)
                        for _, bboxes in bbd_data.items():
                            for bbx in bboxes:
                                if bbx[0] == current_player_id:
                                    frame_id = bbx[5].split("-", 1)[0]
                                    bbx[0] = new_player_id
                                    bbx[5] = f"{frame_id}-{new_player_id}"
                                    bbx[1] = new_team_id
                    # --- bulk team edit (all frames, no player_id changes)
                    if (current_team_id is not None and new_team_id is not None) and (
                        update_all_team_id and not new_player_id): # change team exclusively
                        for _, bboxes in bbd_data.items():
                            for bbx in bboxes:
                                if bbx[1] == current_team_id:
                                    bbx[1] = new_team_id
                    altered_bbx.bboxes = json.dumps(bbd_data)
                    altered_bbx.meta_data = _compute_meta_data(bbd_data)
            logging.info(f"Successfully created new temporary data with id: {altered_bbx.id}")
            # perform the database switch inside a transaction
            with transaction.atomic():
                # re-fetch the object inside the transaction to ensure it's not stale
                # and to lock the row (if using select_for_update)
                prr_to_update = PluginRunResult.objects.get(pk=bytetrack_prr_db.pk)
                prr_to_update.data_id = altered_bbx.id
                prr_to_update.save()
            # if the transaction was successful, clean up the old file
            manager.delete(old_data_id)
            # delete backend cache path of old data
            cache_path = os.path.join(settings.DATA_CACHE_ROOT, f"{bytetrack_prr_db.pk}.json")
            if os.path.exists(cache_path): os.remove(cache_path)
            logging.info(f"Successfully updated DB and deleted old data {old_data_id}.")
            return JsonResponse({"status": "ok", "entry": altered_bbx.to_dict()})
        except Exception as e:
            logging.error(f"Failed to update bounding box data: {e}", exc_info=True)
            # if anything failed, delete the newly created (now orphaned) file
            if altered_bbx and altered_bbx.id:
                logging.warning(f"Rolling back: deleting temporary data {altered_bbx.id}")
                manager.delete(altered_bbx.id)
            # raise  # re-raise the exception so Django's error handling can take over
            return JsonResponse(
                {'status': 'error', 
                 'message': ''
                }, 
                status=500
            )

 
class BoundingBoxesDelete(View):
    @decode_and_authenticate(require_name=False)
    def post(self, request, data):
        try:
            bbox_id = data.get("bbox_id")
            bytetrack_result_id = data.get("bytetrack_run_id")
            player_id_to_delete = None; team_id_to_delete = None
            if "player_id" in data: player_id_to_delete = int(data.get("player_id"))
            if "team_id" in data: team_id_to_delete = int(data.get("team_id"))
            delete_all_player_id = False
            if "delete_all_player_id" in data:
                if data.get("delete_all_player_id") in ['true', 'True', True]:
                    delete_all_player_id = True
            delete_all_team_id = False
            if "delete_all_team_id" in data:
                if data.get("delete_all_team_id") in ['true', 'True', True]:
                    delete_all_team_id = True
  
            # possible update ops.
            CH = None
            if not delete_all_player_id and bbox_id:
                CH='SINGLE_FRAME_DEL'
            if delete_all_player_id and player_id_to_delete:
                CH='ALL_PLAYER_DEL'
            if delete_all_team_id and team_id_to_delete and not player_id_to_delete:
                CH='COMPLETE_TEAM_DEL'
            if not CH: return JsonResponse({"status": "error", "type": "missing_args"})
            else: logging.info(f'running {CH} delete op. on bbox data...')
  
            bytetrack_prr_db = PluginRunResult.objects.get(
                plugin_run_id=bytetrack_result_id
            )
            old_data_id = bytetrack_prr_db.data_id
            logging.info(f"Preparing to delete data for {bytetrack_prr_db.id}... old data_id: {old_data_id}")

            manager = DataManager("/predictions/")
            altered_bbx = None

            # NOTE: look for a more efficient solution;; right now recreates data entry by entry...
            with manager.load(old_data_id) as bboxes_data:
                bbd = bboxes_data.to_dict()
                bbd_data = json.loads(bbd["bboxes"])
                with manager.create_data("BboxesData") as altered_bbx:
                    if not delete_all_player_id and bbox_id:
                        # --- single delete (1 frame); O(n) at worse
                        frame_id = str(bbox_id.split("-", 1)[0])  # only iterate through lists that are related to the frame
                        for bbx_id, bbx in enumerate(bbd_data[frame_id]):
                            # mutate list
                            if bbx[5] == bbox_id:
                                del bbd_data[frame_id][bbx_id]
                                break
                    if delete_all_player_id and player_id_to_delete:
                        # --- bulk delete (all frames); iterates each entry O(n)
                        for frame_id, bboxes in bbd_data.items():
                            for bbx_id, bbx in enumerate(bboxes):
                                if bbx[0] == player_id_to_delete:
                                    del bbd_data[frame_id][bbx_id]
                    # --- bulk team edit (all frames, no player_id changes)
                    if delete_all_team_id and team_id_to_delete and not player_id_to_delete: # delete team exclusively
                        for frame_id, bboxes in bbd_data.items():
                            for bbx_id, bbx in enumerate(bboxes):
                                if bbx[1] == team_id_to_delete:
                                    del bbd_data[frame_id][bbx_id]
                    altered_bbx.bboxes = json.dumps(bbd_data)
                    altered_bbx.meta_data = _compute_meta_data(bbd_data)
            logging.info(f"Successfully created new temporary data with id: {altered_bbx.id}")

            with transaction.atomic():
                prr_to_update = PluginRunResult.objects.get(pk=bytetrack_prr_db.pk)
                prr_to_update.data_id = altered_bbx.id
                prr_to_update.save()

            manager.delete(old_data_id)
            # delete backend cache path of old data
            cache_path = os.path.join(settings.DATA_CACHE_ROOT, f"{bytetrack_prr_db.pk}.json")
            if os.path.exists(cache_path): os.remove(cache_path)
            logging.info(f"Successfully updated DB and deleted old data {old_data_id}.")
            return JsonResponse({"status": "ok", "entry": altered_bbx.to_dict()})
        except Exception as e:
            logging.error(f"Failed to delete bounding box data: {e}", exc_info=True)
            if altered_bbx and altered_bbx.id:
                logging.warning(f"Rolling back: deleting temporary data {altered_bbx.id}")
                manager.delete(altered_bbx.id)

            # raise
            return JsonResponse(
                {'status': 'error', 
                 'message': ''
                }, 
                status=500
            )