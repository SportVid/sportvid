"""Server-sent-event fan-out between the celery workers and the gunicorn processes.

Plugin status/progress is written by the celery worker, but the SSE stream that pushes
it to the browser is held open by a *different* process (gunicorn). valkey pub/sub is
the bridge -- it's already in the stack as the celery broker, so nothing new is added
to the deployment.

One channel per user keeps authorization trivial: a stream only ever subscribes to the
channel of the user it authenticated as.
"""
import os
import json
import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "sportvid:events"
# Separate namespace from the per-user event channels above -- one channel per
# cancellable resource (a video conversion, a plugin run), so a running task can
# subscribe to exactly its own id instead of filtering someone else's stream.
CANCEL_CHANNEL_PREFIX = "sportvid:cancel"

# How long a single SSE connection is kept open before it's closed on purpose. The
# browser's EventSource reconnects on its own, which keeps proxies from silently
# dropping a socket we still believe in.
STREAM_MAX_LIFETIME = 600.0
STREAM_KEEPALIVE_INTERVAL = 20.0

_client = None
_client_lock = threading.Lock()


def channel_for_user(user_id) -> str:
    return f"{CHANNEL_PREFIX}:{user_id}"


def get_client():
    """Lazily built valkey client, shared per process."""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            import valkey

            host = os.environ.get("VALKEY_CLIENT_HOST", "valkey")
            port = int(os.environ.get("VALKEY_INTERNAL_PORT", 6380))
            _client = valkey.Valkey(host=host, port=port, socket_keepalive=True)
    return _client


def publish(user_id, payload: dict) -> None:
    """Fire-and-forget. A broken valkey must never take a running plugin down with it."""
    if user_id is None:
        return
    try:
        # Same encoder JsonResponse uses, so an entry arriving over the stream is byte
        # for byte what the REST endpoints hand out -- in particular datetimes stay
        # "...T...Z" instead of turning into str(datetime), which the frontend's date
        # formatting would slice apart wrongly.
        from django.core.serializers.json import DjangoJSONEncoder

        get_client().publish(
            channel_for_user(user_id), json.dumps(payload, cls=DjangoJSONEncoder)
        )
    except Exception:
        logger.warning("Failed to publish event to user %s", user_id, exc_info=True)


def owner_id_for_video(video_id):
    """Video owner behind a plugin run, cached -- this is hit on every progress tick."""
    if video_id is None:
        return None
    from django.core.cache import cache
    from backend.models import Video

    key = f"event_video_owner:{video_id}"
    # The cache is a convenience here, never a dependency -- this runs inside a post_save
    # signal on every progress tick, and an unreachable memcached must not take a running
    # plugin down with it.
    try:
        owner_id = cache.get(key)
    except Exception:
        logger.debug("Owner cache lookup failed", exc_info=True)
        owner_id = None
    if owner_id is not None:
        return owner_id
    owner_id = (
        Video.objects.filter(id=video_id).values_list("owner_id", flat=True).first()
    )
    if owner_id is not None:
        try:
            cache.set(key, owner_id)
        except Exception:
            logger.debug("Owner cache write failed", exc_info=True)
    return owner_id


def publish_plugin_run(plugin_run) -> None:
    owner_id = owner_id_for_video(plugin_run.video_id)
    if owner_id is None:
        return
    publish(owner_id, {"type": "plugin_run.update", "entry": plugin_run.to_dict()})


def publish_plugin_run_deleted(plugin_run) -> None:
    owner_id = owner_id_for_video(plugin_run.video_id)
    if owner_id is None:
        return
    publish(owner_id, {"type": "plugin_run.deleted", "id": plugin_run.id.hex})


def publish_video(video) -> None:
    """`video` may be a Video instance or an id -- the latter for the queryset-update
    paths in convert_video.py, which don't hold a fresh instance."""
    from backend.models import Video

    if not isinstance(video, Video):
        video = Video.objects.filter(id=video).first()
        if video is None:
            return
    if video.owner_id is None:
        return
    publish(video.owner_id, {"type": "video.update", "entry": video.to_dict()})


def subscribe(user_id):
    """Yields raw event payload strings for `user_id` until the stream's lifetime is up.

    Emits SSE keepalive comments so the connection isn't mistaken for dead by proxies,
    and closes itself after STREAM_MAX_LIFETIME -- the client reconnects.
    """
    import time

    pubsub = get_client().pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel_for_user(user_id))
    try:
        yield ": connected\n\n"
        deadline = time.monotonic() + STREAM_MAX_LIFETIME
        last_keepalive = time.monotonic()
        while time.monotonic() < deadline:
            message = pubsub.get_message(timeout=1.0)
            if message and message.get("type") == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield f"data: {data}\n\n"
                continue
            now = time.monotonic()
            if now - last_keepalive >= STREAM_KEEPALIVE_INTERVAL:
                last_keepalive = now
                yield ": keepalive\n\n"
    finally:
        try:
            pubsub.close()
        except Exception:
            logger.debug("Failed to close pubsub cleanly", exc_info=True)


# ---------------------------------------------------------------------------------
# Cancellation: push, not poll.
#
# A long-running task (HLS conversion, a plugin run) subscribes to its own valkey
# channel and reacts the instant a cancel message arrives, instead of periodically
# re-querying the database to check whether it's still wanted. Uses the same valkey
# instance/connection helper as the event stream above -- nothing new added to the
# deployment.
# ---------------------------------------------------------------------------------


def cancel_channel(kind, resource_id) -> str:
    return f"{CANCEL_CHANNEL_PREFIX}:{kind}:{resource_id}"


def publish_cancel(kind, resource_id) -> None:
    """Fire-and-forget, like publish() -- an unreachable valkey must never block a
    delete. Whoever's listening (if anyone still is) reacts immediately; if nobody's
    listening (already finished, or the subscribe/publish raced) there's simply
    nothing left to cancel."""
    try:
        get_client().publish(cancel_channel(kind, resource_id), "cancel")
    except Exception:
        logger.warning("Failed to publish cancel for %s %s", kind, resource_id, exc_info=True)


@contextmanager
def cancellation_watcher(kind, resource_id, on_cancel=None):
    """Yields a threading.Event that's set the moment publish_cancel(kind, resource_id)
    is called, for the lifetime of the `with` block.

    A dedicated background thread blocks on the valkey subscription and reacts as soon
    as a message arrives -- the caller doesn't need to re-check anything on a timer.
    `on_cancel`, if given, runs on that *listener thread* itself, right when the
    message arrives, for callers that need to act immediately rather than waiting for
    their own next loop iteration (e.g. killing a subprocess).

    If valkey itself is unreachable, this degrades to an Event that simply never gets
    set -- the caller falls back to whatever timeout/other checks it already has,
    rather than crashing a running task over a broken cancel channel.
    """
    event = threading.Event()

    try:
        pubsub = get_client().pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(cancel_channel(kind, resource_id))
    except Exception:
        logger.warning(
            "Cancellation watcher unavailable for %s %s -- delete won't cancel it instantly",
            kind, resource_id, exc_info=True,
        )
        yield event
        return

    stop = threading.Event()

    def _listen():
        try:
            while not stop.is_set():
                message = pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    event.set()
                    if on_cancel is not None:
                        try:
                            on_cancel()
                        except Exception:
                            logger.exception(
                                "on_cancel callback failed for %s %s", kind, resource_id
                            )
                    return
        except Exception:
            logger.warning(
                "Cancellation listener crashed for %s %s", kind, resource_id, exc_info=True
            )

    thread = threading.Thread(
        target=_listen, name=f"cancel-watch-{kind}-{resource_id}", daemon=True
    )
    thread.start()
    try:
        yield event
    finally:
        # Not joined on purpose -- the listener notices `stop` and exits within one
        # get_message() timeout (<=1s) on its own; waiting for that here would make
        # every normal (non-cancelled) completion pay up to a second for nothing.
        stop.set()
        try:
            pubsub.close()
        except Exception:
            pass
