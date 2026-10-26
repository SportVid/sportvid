"""Per-user storage quota (audit S4).

`used_storage_size` counts uploaded videos and tracking data. Uploads check the quota
before anything is written, and the counter is changed with single UPDATE statements,
so parallel requests cannot overwrite each other's changes.
"""
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.http import JsonResponse


def _users():
    from backend.models import SportVidUser

    return SportVidUser.objects


def would_exceed_quota(user, size: int) -> bool:
    """True if storing `size` more bytes would take `user` over max_storage_size."""
    used, limit = _users().filter(pk=user.pk).values_list("used_storage_size", "max_storage_size").get()
    return used + size > limit


def quota_exceeded_response():
    return JsonResponse({"status": "error", "type": "quota_exceeded"}, status=413)


def add_used_storage(user, size: int) -> None:
    _users().filter(pk=user.pk).update(used_storage_size=F("used_storage_size") + size)
    user.refresh_from_db(fields=["used_storage_size"])


def release_used_storage(user, size: int) -> None:
    _users().filter(pk=user.pk).update(used_storage_size=Greatest(F("used_storage_size") - size, Value(0)))
    user.refresh_from_db(fields=["used_storage_size"])
