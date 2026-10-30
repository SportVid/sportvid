import json
import logging
from django.views import View
from django.http import JsonResponse

from backend.models import (
    AnnotationShortcut, 
    Shortcut, 
    Video, 
    Annotation
)
from backend.permissions import readable, writable
from backend.utils.api import ApiView


logger = logging.getLogger(__name__)


def shortcut_for_keys(keys, user, video=None, type=None):
    """The user's shortcut for this key combination (and video), created if missing."""
    keys_string = Shortcut.generate_keys_string(keys)
    shortcut_db, _ = Shortcut.objects.get_or_create(
        keys_string=keys_string, video=video, owner=user, type=type, defaults={"keys": keys}
    )
    return shortcut_db


def assign_shortcut(annotation, keys, user, video=None):
    """Bind `keys` to `annotation`, replacing the annotation's previous shortcut."""
    shortcut_db = shortcut_for_keys(keys, user, video=video, type="annotation")
    annotation_shortcut_db, _ = AnnotationShortcut.objects.update_or_create(
        annotation=annotation, defaults={"shortcut": shortcut_db}
    )
    return annotation_shortcut_db, shortcut_db


def valid_keys(keys):
    return isinstance(keys, list) and len(keys) > 0 and all(isinstance(k, str) and k for k in keys)


class AnnotationShortcutCreate(ApiView):
    """Bind a key combination to one annotation: {"annotation_id", "keys": [...], "video_id"?}."""

    def post(self, request):
        data = request.data
        try:
            if "annotation_id" not in data or not valid_keys(data.get("keys")):
                return JsonResponse({"status": "error", "type": "missing_values"})

            video_db = None
            if "video_id" in data:
                video_db = writable(Video, request.user).filter(id=data.get("video_id")).first()
                if video_db is None:
                    return JsonResponse({"status": "error", "type": "not_exist"})
            annotation_db = writable(Annotation, request.user).filter(id=data.get("annotation_id")).first()
            if annotation_db is None:
                return JsonResponse({"status": "error", "type": "not_exist"})

            annotation_shortcut_db, shortcut_db = assign_shortcut(
                annotation_db, data.get("keys"), request.user, video=video_db
            )
            return JsonResponse(
                {"status": "ok", "entry": annotation_shortcut_db.to_dict(), "shortcut": shortcut_db.to_dict()}
            )
        except Exception:
            logger.exception("Failed to create annotation shortcut")
            return JsonResponse({"status": "error"})


class AnnotationShortcutUpdate(ApiView):
    def delete_shortcut(self, annotation_shortcut, user, annotation, video=None):
        AnnotationShortcut.objects.filter(annotation=annotation).delete()

    def update_shortcut(self, annotation_shortcut, user, annotation, video=None):
        annotation_shortcut_db, shortcut_db = assign_shortcut(
            annotation, annotation_shortcut.get("keys"), user, video=video
        )
        return {"annotation_shortcut": annotation_shortcut_db, "shortcut": shortcut_db}

    def post(self, request):
        try:
            data = request.data

            if "annotation_shortcuts" not in data:
                return JsonResponse({"status": "error", "type": "missing_values"})

            annotation_shortcuts = data.get("annotation_shortcuts")
            if not isinstance(annotation_shortcuts, list):
                return JsonResponse({"status": "error", "type": "wrong_type"})

            video_db = None
            if "video_id" in data:
                try:
                    video_db = writable(Video, request.user).get(id=data.get("video_id"))
                except Video.DoesNotExist:
                    return JsonResponse({"status": "error", "type": "not_exist"})

            results = []
            for annotation_shortcut in annotation_shortcuts:
                if "id" not in annotation_shortcut:
                    continue
                annotation_db = None
                try:
                    annotation_db = writable(Annotation, request.user).get(id=annotation_shortcut.get("id"))
                except Annotation.DoesNotExist:
                    continue

                if "keys" not in annotation_shortcut:
                    self.delete_shortcut(
                        annotation_shortcut, user=request.user, annotation=annotation_db, video=video_db
                    )
                else:
                    keys = annotation_shortcut.get("keys")
                    if not isinstance(keys, list) or len(keys) == 0:
                        self.delete_shortcut(
                            annotation_shortcut, user=request.user, annotation=annotation_db, video=video_db
                        )
                    else:
                        shortcuts = self.update_shortcut(
                            annotation_shortcut, user=request.user, annotation=annotation_db, video=video_db
                        )
                        results.append(shortcuts)

            return JsonResponse(
                {
                    "status": "ok",
                    "annotation_shortcuts": [x["annotation_shortcut"].to_dict() for x in results],
                    "shortcuts": [x["shortcut"].to_dict() for x in results],
                }
            )

        except Exception:
            logger.exception('Failed to update AnnotationShortcut')
            return JsonResponse({"status": "error"})


class AnnotationShortcutList(ApiView):
    def get(self, request):
        try:

            query_args = {}

            if "video_id" in request.GET:
                query_args["shortcut__video__id"] = request.GET.get("video_id")

            query_results = readable(AnnotationShortcut, request.user).filter(**query_args)

            entries = []
            for shortcut in query_results:
                entries.append(shortcut.to_dict())
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception('Failed to list annotation shortcuts')
            return JsonResponse({"status": "error"})
