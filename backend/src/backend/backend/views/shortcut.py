import json
import logging
from django.views import View
from django.http import JsonResponse

from backend.models import Shortcut, Video
from backend.permissions import writable
from backend.views.annotation_shortcut import shortcut_for_keys, valid_keys
from backend.utils.api import ApiView


logger = logging.getLogger(__name__)


class ShortcutCreate(ApiView):
    def post(self, request):
        try:
            data = request.data

            # "keys": ["ctrl", "a"], or "key": "ctrl+a" as stores/shortcut.js sends it
            keys = data.get("keys")
            if keys is None and isinstance(data.get("key"), str):
                keys = data["key"].split("+")
            if not valid_keys(keys):
                return JsonResponse({"status": "error", "type": "missing_values"})

            video_db = None
            if "video_id" in data:
                video_db = writable(Video, request.user).filter(id=data.get("video_id")).first()
                if video_db is None:
                    return JsonResponse({"status": "error", "type": "not_exist"})

            shortcut_db = shortcut_for_keys(keys, request.user, video=video_db, type=data.get("type"))
            return JsonResponse({"status": "ok", "entry": shortcut_db.to_dict()})
        except Exception:
            logger.exception("Failed to create shortcut")
            return JsonResponse({"status": "error"})


class ShortcutList(ApiView):
    def get(self, request):
        try:

            query_args = {}
            query_args["owner"] = request.user
            if "video_id" in request.GET:
                query_args["video__id"] = request.GET.get("video_id")
            query_results = Shortcut.objects.filter(**query_args)

            entries = []
            for shortcut in query_results:
                entries.append(shortcut.to_dict())
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception("Failed to list shortcuts")
            return JsonResponse({"status": "error"})
