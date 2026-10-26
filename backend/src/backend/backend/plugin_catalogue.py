"""Which plugins can run right now (audit B6, docs/adr/0003).

A backend plugin can run only if every Ray Serve plugin its task calls
(`Task.ray_plugins`) is deployed and running. The analyser reports the running Ray
plugins and their versions (`list_plugins`); the answer is cached briefly.

If the analyser cannot be asked, `available_plugins()` returns None and callers keep
the previous behaviour (offer and accept every registered plugin).
"""
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = "plugin_catalogue:deployed_ray_plugins"
CACHE_SECONDS = 30
GRPC_TIMEOUT_SECONDS = 5


def deployed_ray_plugins():
    """{ray plugin name: version} of the running Ray plugins, or None if unknown."""
    deployed = cache.get(CACHE_KEY)
    if deployed is not None:
        return deployed
    try:
        import grpc
        from interface import analyser_pb2, analyser_pb2_grpc

        with grpc.insecure_channel(f"{settings.GRPC_HOST}:{settings.GRPC_PORT}") as channel:
            reply = analyser_pb2_grpc.AnalyserStub(channel).list_plugins(
                analyser_pb2.ListPluginsRequest(), timeout=GRPC_TIMEOUT_SECONDS
            )
        deployed = {plugin.name: plugin.version for plugin in reply.plugins}
    except Exception:
        logger.warning("Could not ask the analyser which plugins are deployed", exc_info=True)
        return None
    cache.set(CACHE_KEY, deployed, CACHE_SECONDS)
    return deployed


def available_plugins():
    """Sorted names of the backend plugins that can run now, or None if unknown."""
    from backend.plugin_manager import PluginManager

    deployed = deployed_ray_plugins()
    if deployed is None:
        return None
    return sorted(
        name for name, task_cls in PluginManager._plugins.items()
        if set(getattr(task_cls, "ray_plugins", ())) <= set(deployed)
    )


def is_available(plugin: str) -> bool:
    available = available_plugins()
    return True if available is None else plugin in available
