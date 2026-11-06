import logging
import json
from django.views import View
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse

from backend.models import ClusterItem, ClusterTimelineItem
from backend.permissions import readable, writable
from backend.utils.api import ApiView


logger = logging.getLogger(__name__)


class ClusterItemFetch(ApiView):
    def get(self, request):
        try:

            entries = [
                item.to_dict()
                for item in readable(ClusterItem, request.user).filter(video_id=request.GET.get('video_id'))
            ]

            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception('Failed to fetch cluster items')
            return JsonResponse({"status": "error"})


class ClusterItemDelete(ApiView):
    def post(self, request):
        try:
            data = request.data

            if "item_ids" not in data:
                return JsonResponse(
                    {"status": "error", "type": "missing_values_plugin_item_ref_list"}
                )
            if "cluster_id" not in data:
                return JsonResponse(
                    {"status": "error", "type": "missing_values_cluster_id"}
                )

            items = writable(ClusterItem, request.user).filter(id__in=list(data.get("item_ids")))
            deleted_ids = [item_id.hex for item_id in items.values_list("id", flat=True)]
            items.delete()

            return JsonResponse({"status": "ok", "entries": deleted_ids})

        except Exception:
            logger.exception('Failed to delete cluster item set')
            return JsonResponse({"status": "error_cluster_item_set_deleted"})


class ClusterItemMove(ApiView):
    def post(self, request):
        try:
            data = request.data

            # the target cluster must be writable too
            writable(ClusterTimelineItem, request.user).get(id=data['new_cluster_id'])
            (writable(ClusterItem, request.user).filter(id__in=data['item_ids'])
                                .update(cluster_timeline_item=data['new_cluster_id']))
            return JsonResponse({"status": "ok"})
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception('Failed to delete cluster timeline item')
            return JsonResponse({"status": "error"})
