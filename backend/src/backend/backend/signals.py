"""Turns model writes into live events for the frontend.

Hooking post_save instead of sprinkling publish() calls means every existing write
path is covered for free -- the once-a-second polling loop in
utils/analyser_client.py::get_plugin_results, every error path in TaskAnalyserClient,
and the DONE/ERROR writes in plugin_manager.py::run_plugin.

Note that queryset .update() does NOT fire post_save; those call sites (see
tasks/convert_video.py) publish explicitly.
"""
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

# Last (status, progress) we actually published, per run. The analyser polling loop
# saves the run every second whether or not anything changed -- without this the
# stream would be pure noise, and the in_scheduler bookkeeping save in plugin_manager
# would emit a pointless event too.
_last_published = {}
_PROGRESS_RESOLUTION = 3
_LAST_PUBLISHED_MAX = 5000


@receiver(post_save, sender=PluginRun, dispatch_uid="backend_plugin_run_event")
def on_plugin_run_saved(sender, instance, **kwargs):
    try:
        key = instance.id
        fingerprint = (
            instance.status,
            round(instance.progress or 0.0, _PROGRESS_RESOLUTION),
        )
        if _last_published.get(key) == fingerprint:
            return
        if len(_last_published) > _LAST_PUBLISHED_MAX:
            # Long-lived worker process -- drop the history rather than grow forever.
            _last_published.clear()
        _last_published[key] = fingerprint
        publish_plugin_run(instance)
    except Exception:
        # Never let event bookkeeping fail the write that triggered it.
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
