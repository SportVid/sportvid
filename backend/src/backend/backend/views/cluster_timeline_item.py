import json
import logging
import uuid
from django.views import View
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse

from backend.models import ClusterTimelineItem, Video, PluginRun
from backend.permissions import readable, writable
from backend.utils.api import ApiView


logger = logging.getLogger(__name__)


class ClusterTimelineItemCreate(ApiView):
    def post(self, request):
        try:
            data = request.data

            video = writable(Video, request.user).get(id=data["video_id"])
            plugin_run = writable(PluginRun, request.user).get(id=uuid.UUID(data['plugin_run']))
            cluster_timeline_item = ClusterTimelineItem.objects.create(
                cluster_id=uuid.uuid4(),
                name=data["name"],
                video=video,
                plugin_run=plugin_run,
                type=data['type']
            )

            return JsonResponse({"status": "ok", "entry": cluster_timeline_item.to_dict()})
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception('Failed to create cluster timeline item')
            return JsonResponse({"status": "error", "type" : "general"})
        
class ClusterTimelineItemDelete(ApiView):
    def post(self, request):
        try:
            data = request.data
            count, _ = writable(ClusterTimelineItem, request.user).filter(id=data.get("id")).delete()
            if count:
                return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "error", "type": "not_exist"})
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception('Failed to delete cluster timeline item')
            return JsonResponse({"status": "error"})


class ClusterTimelineItemRename(ApiView):
    def post(self, request):
        try:
            data = request.data

            if "cti_id" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})
            if "name" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})
            if not isinstance(data.get("name"), str):
                return JsonResponse({"status": "error", "type": "wrong_request_body"})

            try:
                cti = writable(ClusterTimelineItem, request.user).get(id=data.get("cti_id"))
            except ClusterTimelineItem.DoesNotExist:
                return JsonResponse({"status": "error", "type": "not_exist"})

            cti.name = data.get("name")
            cti.save()
            return JsonResponse({"status": "ok", "entry": cti.to_dict()})
        except Exception:
            logger.exception('Failed to rename cluster timeline item')
            return JsonResponse({"status": "error"})

class ClusterTimelineItemFetch(ApiView):
    def get(self, request):
        try:
            
            video_id = uuid.UUID(hex=request.GET.get('video_id'))
            entries = [
                cti.to_dict()
                for cti in readable(ClusterTimelineItem, request.user).filter(video_id=video_id)
            ]

            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception('Failed to fetch cluster timeline item')
            return JsonResponse({"status": "error"})


class ClusterTimelineItemMerge(ApiView):
    def post(self, request):
        try:
            data = request.data
            
            if 'from_id' not in data or 'to_id' not in data:
                return JsonResponse({'status': 'error', 'type': 'Params missing'})

            from_cluster = writable(ClusterTimelineItem, request.user).get(id=data['from_id'])
            writable(ClusterTimelineItem, request.user).get(id=data['to_id'])

            from_cluster.items.update(cluster_timeline_item_id=data['to_id'])
            from_cluster.delete()
            return JsonResponse({'status': 'ok'})

        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})
        except:
            logger.exception('Failed to merge clusters')
            return JsonResponse({"status": "error"})
