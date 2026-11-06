""" Connects django's post_save / post_delte signals to event publishing.
Every PluginRun or Video save (except queryset .update()) emits an live event,
with basic deduplication for frequent progress saves.
"""

# TODO: Signals fire outside transactions.
# post_save handlers call publish_*() directly. If the save is inside a transaction that later rolls back, the event is still published.
# --> Wrap event publishing in transaction.on_commit(...).
# TODO: In-memory deduplication is process-local and fragile.
# _last_published is a plain dict per process; it does not guarantee global dedup and can suppress legitimate events if other fields change.
# --> Consider removing or simplifying the in-memory dedup, or move it to a cache/DB-backed mechanism.
# TODO: No transaction safety
# --> Document that .update() paths must call publish_*() explicitly (already noted in comments, but make it explicit in code).

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from backend.models import PluginRun, Video
from backend.utils.events import (
    publish_plugin_run,
    publish_plugin_run_deleted,
    publish_video,
)


logger = logging.getLogger(__name__)

# NOTE: Maintains an in-memory dedup cache.
#   Analyser polling loop saves run every second.
_last_published = {}
_PROGRESS_RESOLUTION = 3
_LAST_PUBLISHED_MAX = 5000


@receiver(post_save, sender=PluginRun, dispatch_uid="backend_plugin_run_event")
def on_plugin_run_saved(sender, instance, **kwargs):
    """ This post_save handler computes a fingerprint from instance status & progress.
    If the fingerprint remains unchanged, skips publishing.
    """
    try:
        # build fingerprint
        key = instance.id
        fingerprint = (
            instance.status,
            round(instance.progress or 0.0, _PROGRESS_RESOLUTION),
        )
        if _last_published.get(key) == fingerprint:
            return
        if len(_last_published) > _LAST_PUBLISHED_MAX:
            # clears _last_publish_ if it exceeds a limit to stop it from ever growing
            _last_published.clear()
        _last_published[key] = fingerprint
        publish_plugin_run(instance)
    except Exception:
        logger.warning("Failed to emit plugin run event", exc_info=True)


@receiver(post_delete, sender=PluginRun, dispatch_uid="backend_plugin_run_deleted_event")
def on_plugin_run_deleted(sender, instance, **kwargs):
    try:
        _last_published.pop(instance.id, None)
        publish_plugin_run_deleted(instance)
    except Exception:
        logger.warning("Failed to emit plugin run delete event", exc_info=True)


@receiver(post_save, sender=Video, dispatch_uid="backend_video_event")
def on_video_saved(sender, instance, **kwargs):
    try:
        publish_video(instance)
    except Exception:
        logger.warning("Failed to emit video event", exc_info=True)
