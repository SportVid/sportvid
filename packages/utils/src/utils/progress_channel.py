"""Cross-service plugin-progress channel.

The analyser gRPC server hands each plugin run a ``job_id`` and then can only make a
single blocking HTTP call to Ray Serve for the result -- there is no return path for
incremental progress. This bridges that gap over the valkey instance that is already
in the stack (celery broker + SSE bus):

    Ray deployment  --write-->  valkey  key: analyser:progress:<job_id>
    analyser GetPluginStatus  --read-->  reports it to the backend

Every function here is best-effort and never raises: a progress channel hiccup must
not break a plugin run or the status endpoint.
"""

import os
import logging

logger = logging.getLogger(__name__)

_KEY_PREFIX = "analyser:progress"
_TTL_SECONDS = 3600

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    import valkey

    host = (
        os.environ.get("VALKEY_CLIENT_HOST")
        or os.environ.get("VALKEY_INTERNAL_HOST")
        or "valkey"
    )
    port = int(os.environ.get("VALKEY_INTERNAL_PORT", 6380))
    _client = valkey.Valkey(
        host=host, port=port, socket_timeout=2.0, socket_connect_timeout=2.0,
        socket_keepalive=True,
    )
    return _client


def progress_key(job_id: str) -> str:
    return f"{_KEY_PREFIX}:{job_id}"


def publish_progress(job_id: str, progress) -> None:
    """Store 0..1 progress for ``job_id`` (with a TTL so stale keys expire)."""
    if not job_id:
        return
    try:
        value = max(0.0, min(1.0, float(progress)))
        _get_client().set(progress_key(job_id), repr(value), ex=_TTL_SECONDS)
    except Exception:
        logger.debug("progress publish failed for %s", job_id, exc_info=True)


def read_progress(job_id: str):
    """Return stored progress as a 0..1 float, or ``None`` if unknown/unavailable."""
    if not job_id:
        return None
    try:
        raw = _get_client().get(progress_key(job_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return max(0.0, min(1.0, float(raw)))
    except Exception:
        logger.debug("progress read failed for %s", job_id, exc_info=True)
        return None


def clear_progress(job_id: str) -> None:
    if not job_id:
        return
    try:
        _get_client().delete(progress_key(job_id))
    except Exception:
        logger.debug("progress clear failed for %s", job_id, exc_info=True)
