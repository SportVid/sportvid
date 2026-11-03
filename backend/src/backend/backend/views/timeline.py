from django.core.exceptions import ObjectDoesNotExist
import json
import logging
from django.views import View
from django.http import JsonResponse

from backend.models import Video, Timeline, TimelineSegment, PluginRunResult
from backend.permissions import readable, writable
from backend.utils.api import ApiView


logger = logging.getLogger(__name__)


class TimelineList(ApiView):
    def get(self, request):
        try:
            
            video_id = request.GET.get("video_id")
            if video_id:
                video_db = readable(Video, request.user).get(id=video_id)
                timelines = Timeline.objects.filter(video=video_db)
            else:
                timelines = readable(Timeline, request.user)
            
            timelines = (
                timelines.select_related("video")
                .select_related("plugin_run_result")
                .prefetch_related("timelinesegment_set")
            )

            entries = []
            for timeline in timelines:
                result = timeline.to_dict()
                entries.append(result)
            return JsonResponse({"status": "ok", "entries": entries})
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception("Failed to list timelines")
            return JsonResponse({"status": "error"})


class TimelineListAll(ApiView):
    def get(self, request):
        try:
            
            timelines = (
                Timeline.objects.filter(
                    video__owner=request.user).prefetch_related('plugin_run_result'))
            add_results_type = request.GET.get("add_results_type", False)

            entries = []
            for timeline in timelines:
                result = timeline.to_dict()
                if add_results_type:
                    result['plugin'] = {'type': None}
                    if timeline.plugin_run_result:
                        result['plugin']['type'] = PluginRunResult.TYPE[timeline.plugin_run_result.type]
                entries.append(result)
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception("Failed to list all timelines")
            return JsonResponse({"status": "error"})


class TimelineDuplicate(ApiView):
    def post(self, request):
        try:
            data = request.data
            # get timeline entry to duplicate
            timeline_db = writable(Timeline, request.user).get(id=data.get("id"))
            if not timeline_db:
                return JsonResponse({"status": "error", "type": "not_exist"})

            include_annotations = True
            if data.get("include_annotations") is not None and isinstance(data.get("include_annotations"), bool):
                include_annotations = data.get("include_annotations")

            new_timeline_db = timeline_db.clone(include_annotations=include_annotations)

            if data.get("name") and isinstance(data.get("name"), str):
                new_timeline_db["timeline_added"].name = data.get("name")
                new_timeline_db["timeline_added"].save()

            return JsonResponse(
                {
                    "status": "ok",
                    "timeline_added": [new_timeline_db["timeline_added"].to_dict()],
                    "timeline_segment_added": [x.to_dict() for x in new_timeline_db["timeline_segment_added"]],
                    "timeline_segment_annotation_added": [
                        x.to_dict() for x in new_timeline_db["timeline_segment_annotation_added"]
                    ],
                }
            )
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception("Failed to duplicate timeline")
            return JsonResponse({"status": "error"})


class TimelineCreate(ApiView):
    def post(self, request):
        try:
            data = request.data

            if "video_id" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})

            create_args = {"type": "A"}
            try:
                video_db = writable(Video, request.user).get(id=data.get("video_id"))
                create_args["video"] = video_db
                create_args["order"] = Timeline.objects.filter(video=video_db).count()
            except Video.DoesNotExist:
                return JsonResponse({"status": "error", "type": "not_exist"})

            if "name" not in data:
                create_args["name"] = "timeline"
            elif not isinstance(data.get("name"), str):
                return JsonResponse({"status": "error", "type": "wrong_request_body"})
            else:
                create_args["name"] = data.get("name")
            timeline_db = Timeline.objects.create(**create_args)
            timeline_added = [timeline_db.to_dict()]
            timeline_segment_added = [
                TimelineSegment.objects.create(timeline=timeline_db, start=0.0, end=video_db.duration).to_dict()
            ]

            return JsonResponse(
                {
                    "status": "ok",
                    # "entry": timeline_db.to_dict()
                    "timeline_added": timeline_added,
                    "timeline_segment_added": timeline_segment_added,
                }
            )
        except Exception:
            logger.exception("Failed to create timeline")
            return JsonResponse({"status": "error"})


class TimelineRename(ApiView):
    def post(self, request):
        try:
            data = request.data

            if "id" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})
            if "name" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})
            if not isinstance(data.get("name"), str):
                return JsonResponse({"status": "error", "type": "wrong_request_body"})

            try:
                timeline_db = writable(Timeline, request.user).get(id=data.get("id"))
            except Timeline.DoesNotExist:
                return JsonResponse({"status": "error", "type": "not_exist"})

            timeline_db.name = data.get("name")
            timeline_db.save()
            return JsonResponse({"status": "ok", "entry": timeline_db.to_dict()})
        except Exception:
            logger.exception("Failed to rename timeline")
            return JsonResponse({"status": "error"})


class TimelineChangeVisualization(ApiView):
    def post(self, request):
        try:
            data = request.data

            if "id" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})
            if "visualization" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})
            if not isinstance(data.get("visualization"), str):
                return JsonResponse({"status": "error", "type": "wrong_request_body"})

            try:
                timeline_db = writable(Timeline, request.user).get(id=data.get("id"))
            except Timeline.DoesNotExist:
                return JsonResponse({"status": "error", "type": "not_exist"})

            if data.get("visualization") not in timeline_db.VISUALIZATION.values():
                return JsonResponse({"status": "error", "type": "wrong_value"})

            inv_map = {v: k for k, v in timeline_db.VISUALIZATION.items()}
            timeline_db.visualization = inv_map[data.get("visualization")]

            colormap = data.get("colormap")
            if colormap is not None:
                if not isinstance(colormap, str):
                    return JsonResponse({"status": "error", "type": "wrong_request_body"})
                timeline_db.colormap = colormap

            colormap_inverse = data.get("colormap_inverse")
            if colormap_inverse is not None:
                logger.debug("colormap_inverse: %s", colormap_inverse)
                if not isinstance(colormap_inverse, bool):
                    return JsonResponse({"status": "error", "type": "wrong_request_body"})
                timeline_db.colormap_inverse = colormap_inverse
            

            timeline_db.save()
            return JsonResponse({"status": "ok", "entry": timeline_db.to_dict()})
        except Exception:
            logger.exception("Failed to change timeline visualization")
            return JsonResponse({"status": "error"})


class TimelineSetParent(ApiView):
    def post(self, request):
        try:
            data = request.data

            if "timelineId" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})
            if "parentId" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})

            try:
                timeline_db = writable(Timeline, request.user).get(id=data.get("timelineId"))
            except Timeline.DoesNotExist:
                return JsonResponse({"status": "error", "type": "not_exist"})

            parent_timeline_db = None
            if data.get("parentId"):
                try:
                    parent_timeline_db = writable(Timeline, request.user).get(id=data.get("parentId"))
                except Timeline.DoesNotExist:
                    return JsonResponse({"status": "error", "type": "not_exist"})

            timeline_db.parent = parent_timeline_db
            timeline_db.save()
            return JsonResponse({"status": "ok", "entry": timeline_db.to_dict()})
        except Exception:
            logger.exception("Failed to set timeline parent")
            return JsonResponse({"status": "error"})


class TimelineSetCollapse(ApiView):
    def post(self, request):
        try:
            data = request.data

            if "timelineId" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})
            if "collapse" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})

            try:
                timeline_db = writable(Timeline, request.user).get(id=data.get("timelineId"))

            except Timeline.DoesNotExist:
                return JsonResponse({"status": "error", "type": "not_exist"})

            timeline_db.collapse = data.get("collapse")
            timeline_db.save()
            return JsonResponse({"status": "ok"})
        except Exception:
            logger.exception("Failed to collapse timeline")
            return JsonResponse({"status": "error"})


class TimelineSetOrder(ApiView):
    def post(self, request):
        try:
            data = request.data

            if "order" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})

            for idx, timelineId in enumerate(data.get("order")):
                logger.debug("%s %s", idx, timelineId)
                try:
                    timeline_db = writable(Timeline, request.user).get(id=timelineId)
                except Timeline.DoesNotExist:
                    return JsonResponse({"status": "error", "type": "not_exist"})

                timeline_db.order = idx
                timeline_db.save()
            return JsonResponse({"status": "ok"})
        except Exception:
            logger.exception("Failed to set timeline order")
            return JsonResponse({"status": "error"})


class TimelineDelete(ApiView):
    def post(self, request):
        try:
            data = request.data
            count, _ = writable(Timeline, request.user).filter(id=data.get("id")).delete()
            if count:
                return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "error", "type": "not_exist"})
        except Exception:
            logger.exception("Failed to delete timeline")
            return JsonResponse({"status": "error"})
