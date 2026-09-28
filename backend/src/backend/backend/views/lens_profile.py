import logging
from django.db.models import Count, Q
from django.views import View
from django.http import JsonResponse

from backend.models import LensProfile, Video
from backend.utils.decode_auth import decode_and_authenticate
from backend.utils.lens import is_compatible


logger = logging.getLogger(__name__)


def _supported_only(request) -> bool:
    return request.GET.get("supported_only", "true").lower() != "false"


def _get_video(request):
    """Resolve an optional ?video_id= owned by the requesting user; (video, error_response)."""
    if "video_id" not in request.GET:
        return None, None
    try:
        return Video.objects.get(id=request.GET.get("video_id"), owner=request.user), None
    except (Video.DoesNotExist, ValueError):
        return None, JsonResponse({"status": "error", "type": "not_exist"})


class LensProfileBrandList(View):
    """Brands with their number of profiles, optionally restricted to a ?group=."""
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error", "type": "not_authenticated"})

            query = LensProfile.objects.all()
            if "group" in request.GET:
                query = query.filter(group=request.GET.get("group"))
            if _supported_only(request):
                query = query.filter(unsupported_reason__isnull=True)

            entries = [
                {"brand": x["brand"], "group": x["group"], "num_profiles": x["num_profiles"]}
                for x in query.values("brand", "group").annotate(num_profiles=Count("id")).order_by("brand")
            ]
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception("Failed to list lens profile brands")
            return JsonResponse({"status": "error"})


class LensProfileModelList(View):
    """Camera models of a ?brand= with their number of profiles."""
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error", "type": "not_authenticated"})
            if "brand" not in request.GET:
                return JsonResponse({"status": "error", "type": "missing_values"})

            query = LensProfile.objects.filter(brand=request.GET.get("brand"))
            if _supported_only(request):
                query = query.filter(unsupported_reason__isnull=True)

            entries = [
                {"model": x["model"], "num_profiles": x["num_profiles"]}
                for x in query.values("model").annotate(num_profiles=Count("id")).order_by("model")
            ]
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception("Failed to list lens profile models")
            return JsonResponse({"status": "error"})


class LensProfileList(View):
    """Lens profiles filtered by ?brand=, ?model=, ?group=, ?eis=, ?search=.

    With ?video_id= each entry says whether it can be applied to that video's resolution,
    and ?compatible_only=true drops the ones that can't.
    """
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error", "type": "not_authenticated"})

            video, error = _get_video(request)
            if error is not None:
                return error

            query = LensProfile.objects.all()
            for field in ("brand", "model", "group", "eis"):
                if field in request.GET:
                    query = query.filter(**{field: request.GET.get(field)})
            if request.GET.get("search"):
                search = request.GET.get("search")
                query = query.filter(
                    Q(name__icontains=search) | Q(model__icontains=search) | Q(lens_model__icontains=search)
                )
            if _supported_only(request):
                query = query.filter(unsupported_reason__isnull=True)

            compatible_only = request.GET.get("compatible_only", "false").lower() == "true"
            entries = []
            for lens_profile in query:
                entry = lens_profile.to_dict()
                if video is not None:
                    entry["compatible"] = is_compatible(
                        lens_profile.calib_width, lens_profile.calib_height, video.width, video.height
                    )
                    if compatible_only and not entry["compatible"]:
                        continue
                entries.append(entry)
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception("Failed to list lens profiles")
            return JsonResponse({"status": "error"})


class VideoSetLensProfile(View):
    """Assign a lens profile to a video ({"video_id", "lens_profile_id"}); a null lens_profile_id clears it.

    Existing calibrations keep the intrinsics they were computed with; rerun the
    calibration to apply a changed profile.
    """
    @decode_and_authenticate(require_name=False)
    def post(self, request, data):
        if "video_id" not in data or "lens_profile_id" not in data:
            return JsonResponse({"status": "error", "type": "missing_values"})
        try:
            video = Video.objects.get(id=data.get("video_id"), owner=request.user)
        except (Video.DoesNotExist, ValueError):
            return JsonResponse({"status": "error", "type": "not_exist"})

        lens_profile = None
        if data.get("lens_profile_id") is not None:
            try:
                lens_profile = LensProfile.objects.get(id=data.get("lens_profile_id"))
            except (LensProfile.DoesNotExist, ValueError):
                return JsonResponse({"status": "error", "type": "not_exist"})
            if lens_profile.unsupported_reason is not None:
                return JsonResponse({
                    "status": "error",
                    "type": "unsupported_lens_profile",
                    "reason": lens_profile.unsupported_reason,
                })
            if not is_compatible(lens_profile.calib_width, lens_profile.calib_height, video.width, video.height):
                return JsonResponse({
                    "status": "error",
                    "type": "incompatible_resolution",
                    "reason": (
                        f"lens profile {lens_profile.calib_width}x{lens_profile.calib_height} doesn't match "
                        f"the video's aspect ratio ({video.width}x{video.height})"
                    ),
                })

        video.lens_profile = lens_profile
        video.save(update_fields=["lens_profile"])
        return JsonResponse({"status": "ok", "entry": video.to_dict()})
