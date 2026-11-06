import logging
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.views import View
from django.http import JsonResponse

from backend.models import LensProfile, Video
from backend.utils.lens import MAX_CROP, MIN_CROP, aspect_fit, is_compatible, recording_modes
from backend.utils.api import ApiView


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


def _entry(lens_profile, video):
    """lens_profile.to_dict() plus, for a video, how the profile fits it (see LensProfileList)."""
    entry = lens_profile.to_dict()
    if video is not None:
        entry["compatible"] = is_compatible(
            lens_profile.calib_width, lens_profile.calib_height, video.width, video.height
        )
        entry["aspect_fit"] = aspect_fit(
            lens_profile.calib_width, lens_profile.calib_height, video.width, video.height
        )
        entry["recording_modes"] = recording_modes(lens_profile.raw, video.width, video.height)
    return entry


class LensProfileBrandList(ApiView):
    """Brands with their number of profiles, optionally restricted to a ?group=."""
    def get(self, request):
        try:

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


class LensProfileModelList(ApiView):
    """Camera models of a ?brand= with their number of profiles."""
    def get(self, request):
        try:
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


class LensProfileList(ApiView):
    """Lens profiles filtered by ?brand=, ?model=, ?group=, ?eis=, ?search=.

    With ?video_id= each entry also carries
    - "compatible": the profile was calibrated at the video's aspect ratio (?compatible_only=true drops the others);
    - "aspect_fit": how the video frame relates to the calibrated one (utils/lens.py:aspect_fit). Other aspect
      ratios are applied as a centred crop of the calibrated frame, as GoPro records them;
    - "recording_modes": the EIS crops the video may have been recorded with (utils/lens.py:recording_modes).
    """
    def get(self, request):
        try:

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
                entry = _entry(lens_profile, video)
                if video is not None and compatible_only and not entry["compatible"]:
                    continue
                entries.append(entry)
            return JsonResponse({"status": "ok", "entries": entries})
        except Exception:
            logger.exception("Failed to list lens profiles")
            return JsonResponse({"status": "error"})


class LensProfileGet(ApiView):
    """One lens profile by ?id=, e.g. the one a video is assigned (video "lens_profile_id"), so the
    picker can be pre-filled. With ?video_id= the entry carries the same per-video fields as LensProfileList.

    Unsupported profiles are returned too ("supported": false): a video may still be assigned one that a
    later import marked unsupported.
    """
    def get(self, request):
        try:
            if "id" not in request.GET:
                return JsonResponse({"status": "error", "type": "missing_values"})

            video, error = _get_video(request)
            if error is not None:
                return error
            try:
                lens_profile = LensProfile.objects.get(id=request.GET.get("id"))
            except (LensProfile.DoesNotExist, ValueError, ValidationError):
                return JsonResponse({"status": "error", "type": "not_exist"})

            return JsonResponse({"status": "ok", "entry": _entry(lens_profile, video)})
        except Exception:
            logger.exception("Failed to get lens profile")
            return JsonResponse({"status": "error"})


class VideoSetLensProfile(ApiView):
    """Assign a lens profile to a video ({"video_id", "lens_profile_id", "lens_crop"}); a null lens_profile_id
    clears it. "lens_crop" is the EIS crop of the recording mode (one of the profile's "recording_modes" or a
    measured value), default 1.0.

    Existing calibrations keep the intrinsics they were computed with; rerun the
    calibration to apply a changed profile.
    """
    def post(self, request):
        data = request.data
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
            if aspect_fit(lens_profile.calib_width, lens_profile.calib_height, video.width, video.height) is None:
                return JsonResponse({
                    "status": "error",
                    "type": "incompatible_resolution",
                    "reason": f"unknown resolution (video {video.width}x{video.height})",
                })

        lens_crop = 1.0
        if lens_profile is not None and data.get("lens_crop") is not None:
            try:
                lens_crop = float(data.get("lens_crop"))
            except (TypeError, ValueError):
                lens_crop = float("nan")
            if not MIN_CROP <= lens_crop <= MAX_CROP:
                return JsonResponse({
                    "status": "error",
                    "type": "invalid_lens_crop",
                    "reason": f"lens crop must lie in [{MIN_CROP}, {MAX_CROP}]",
                })

        video.lens_profile = lens_profile
        video.lens_crop = lens_crop
        video.save(update_fields=["lens_profile", "lens_crop"])
        return JsonResponse({"status": "ok", "entry": video.to_dict()})
