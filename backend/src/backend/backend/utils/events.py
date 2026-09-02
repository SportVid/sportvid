"""Server-sent-event fan-out between the celery workers and the gunicorn processes.

Plugin status/progress is written by the celery worker, but the SSE stream that pushes
it to the browser is held open by a *different* process (gunicorn). valkey pub/sub is
the bridge -- it's already in the stack as the celery broker, so nothing new is added
to the deployment.

One channel per user keeps authorization trivial: a stream only ever subscribes to the
channel of the user it authenticated as.
"""


# ---------> Run Status
# TODO: Owner cache has no TTL
# `owner_id_for_video()`caches indefinitely; ownership changes or deletions can leave stale entries.
# --> Add a TTL to the owner cache, e.g. cache.set(key, owner_id, timeout=300).

# TODO: No retry/backoff for Valkey
# `publish()` is fire-and-forget (good), but repeated failures are only logged.
# --> Optionally add a simple backoff or counter for repeated publish failures.

# TODO: No explicit timeout on cache operations
# Cache get/set can block if the backend is misconfigured.
# --> Document that this is best-effort and must not block tasks.

# ---------> Cancellation
# TODO: Listener thread not joined
# The listener thread is intentionally not joined, which is fine, but there is no guard against many short-lived watchers creating many threads over time.
# -- > Consider a bounded thread pool or a shared watcher per resource type.

# TODO: No timeout on pubsub.get_message
# Uses timeout=1.0, which is fine, but if Valkey is slow or the network is flaky, threads can pile up.
# --> Consider a small per-process limit on active watchers if you expect very high churn.

# TODO: No structured logging for cancellation
# Cancellation events are logged, but without correlation IDs (job IDs, video IDs) in a structured way.
# --> Add structured logging fields (e.g. kind, resource_id) consistently.


import os
import json
import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "sportvid:events"
CANCEL_CHANNEL_PREFIX = "sportvid:cancel"
STREAM_MAX_LIFETIME = 600.0
STREAM_KEEPALIVE_INTERVAL = 20.0

_client = None
_client_lock = threading.Lock()


def channel_for_user(user_id) -> str:
    return f"{CHANNEL_PREFIX}:{user_id}"


def get_client():
    """Lazy thread-safe valkey client, shared per process."""
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
    """Publishes to channel_for_user(user_id) via Valkey. """
    if user_id is None:
        return
    try:
        from django.core.serializers.json import DjangoJSONEncoder

        get_client().publish(
            channel_for_user(user_id), json.dumps(payload, cls=DjangoJSONEncoder)
        )
    except Exception:
        logger.warning("Failed to publish event to user %s", user_id, exc_info=True)


def owner_id_for_video(video_id):
    """Video owner behind a plugin run, may be cached.
    This is hit on every progress tick.
    Tries cache first; on miss, queries DB.
    Finally caches the result on success.
    """
    if video_id is None:
        return None
    from django.core.cache import cache
    from backend.models import Video

    key = f"event_video_owner:{video_id}"
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
    if owner_id is None: return
    publish(owner_id, {"type": "plugin_run.update", "entry": plugin_run.to_dict()})


def publish_plugin_run_deleted(plugin_run) -> None:
    owner_id = owner_id_for_video(plugin_run.video_id)
    if owner_id is None: return
    publish(owner_id, {"type": "plugin_run.deleted", "id": plugin_run.id.hex})


def publish_video(video) -> None:
    """Argument `video` may be a Video instance or an id.
    The latter for the queryset-update paths in convert_video.py, which don't hold a fresh instance.
    """
    from backend.models import Video

    if not isinstance(video, Video):
        video = Video.objects.filter(id=video).first()
        if video is None:
            return
    if video.owner_id is None:
        return
    publish(video.owner_id, {"type": "video.update", "entry": video.to_dict()})


def subscribe(user_id):
    """Generator instance that yields raw event payload strings for `user_id` until the stream's lifetime is up.
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

# NOTE: A long-running task (HLS conversion, a plugin run) subscribes to its own valkey
# channel and reacts the instant a cancel message arrives.
# Uses the same valkey instance/connection helper as the event stream above.
def cancel_channel(kind, resource_id) -> str:
    return f"{CANCEL_CHANNEL_PREFIX}:{kind}:{resource_id}"

def publish_cancel(kind, resource_id) -> None:
    """ Publishes a (fire-and-forget) cancellation message for a specific resource, such as:
        - video: <video_id>
        - plugin_run: <plugin_run_id>
    """
    try:
        get_client().publish(cancel_channel(kind, resource_id), "cancel")
    except Exception:
        logger.warning("Failed to publish cancel for %s %s", kind, resource_id, exc_info=True)

@contextmanager
def cancellation_watcher(kind, resource_id, on_cancel=None):
    """Yields a threading.Event that's set the moment publish_cancel(kind, resource_id)
    is called, for the lifetime of the `with` block.
    
    Cancellation is pushed immediately through Valkey.
    
    This context manager:
        - Creates a threading.Event
        - Opens a Valkey pub/sub connection
        - Subscribes to the resource-specific cancellation channel
        - Starts a daemon listener thread
        - Sets the event when a cancellation message arrives
        - Optionally executes `on_cancel()` on the listener thread
        - Closes the pub/sub connection when the context exits
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
                try:
                    message = pubsub.get_message(timeout=1.0)
                except Exception:
                    # socket closed / bad descriptor / connection lost --> exit cleanly.
                    logger.debug(
                        "Cancellation listener lost connection for %s %s",
                        kind, resource_id, exc_info=True,
                    )
                    return
                
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
        finally:
            try:
                pubsub.close()
            except Exception:
                pass

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
