import logging
import traceback
import sys
import os
import json
import uuid
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from typing import Any, Dict, List, Optional, Type
from rest_framework import serializers

from backend.models import (
    PluginRun,
    PluginRunResult,
    Video, 
    SportVidUser,
)
from data import DataManager


logger = logging.getLogger(__name__)


class PluginManager:
    _plugins: Dict[str, Type] = {}
    _serializers: Dict[str, Type] = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def export_plugin(cls, name: str):
        def export_helper(plugin_cls: Type):
            if name in cls._plugins:
                raise ValueError(f"Plugin '{name}' is already registered")
            cls._plugins[name] = plugin_cls
            return plugin_cls
        return export_helper

    @classmethod
    def export_serializer(cls, name: str):
        def export_helper(serializer_cls: Type):
            if name in cls._serializers:
                raise ValueError(f"Serializer for plugin '{name}' is already registered")
            cls._serializers[name] = serializer_cls
            return serializer_cls
        return export_helper

    @staticmethod
    def _stringify_uuids(value: Any) -> Any:
        # DRF's UUIDField yields a native uuid.UUID in validated_data, but the
        # analyser gRPC client only knows how to serialize bool/int/float/str/dict
        # parameter values -- an unconverted UUID trips its "unsupported type" path.
        if isinstance(value, uuid.UUID):
            return value.hex
        if isinstance(value, dict):
            return {k: PluginManager._stringify_uuids(v) for k, v in value.items()}
        if isinstance(value, list):
            return [PluginManager._stringify_uuids(v) for v in value]
        return value

    @classmethod
    def validate_parameters(cls, plugin: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        parameters = parameters or {}
        # logging.error(f'pre validation params: {parameters}')

        serializer_cls = cls.get_serializer(plugin)
        if serializer_cls is None:
            return parameters

        serializer = serializer_cls(data=parameters or {})
        serializer.is_valid(raise_exception=True)
        val_params = cls._stringify_uuids(dict(serializer.validated_data))
        # logging.error(f'validated params: {val_params}')

        return val_params

    def __contains__(self, plugin: str) -> bool:
        return plugin in self._plugins

    @classmethod
    def has_plugin(cls, plugin: str) -> bool:
        return plugin in cls._plugins

    @classmethod
    def has_serializer(cls, plugin: str) -> bool:
        return plugin in cls._serializers

    @classmethod
    def get_plugin(cls, plugin: str) -> Optional[Type]:
        return cls._plugins.get(plugin)

    @classmethod
    def get_serializer(cls, plugin: str) -> Optional[Type]:
        return cls._serializers.get(plugin)

    @classmethod
    def get_plugin_or_raise(cls, plugin: str) -> Type:
        plugin_cls = cls.get_plugin(plugin)
        if plugin_cls is None:
            raise KeyError(f"Unknown plugin '{plugin}'")
        return plugin_cls

    @classmethod
    def get_serializer_or_raise(cls, plugin: str) -> Type:
        serializer_cls = cls.get_serializer(plugin)
        if serializer_cls is None:
            raise KeyError(f"No serializer registered for plugin '{plugin}'")
        return serializer_cls

    @classmethod
    def list_plugins(cls) -> List[str]:
        return sorted(cls._plugins.keys())

    def run(
        self,
        plugin: str,
        video: Video,
        user: SportVidUser,
        parameters: Optional[Dict[str, Any]] = None,
        run_async: bool = True,
        dry_run: bool = False,
        **kwargs,
    ):
        parameters = parameters or {}
        
        if plugin not in self._plugins:
            return {"status": False, "error": "unknown_plugin"}

        logger.info(
            'User "%s" has started plugin "%s" with parameters %s',
            user.username,
            plugin,
            parameters,
        )

        try:
            validated_parameters = self.validate_parameters(plugin, parameters)
        except serializers.ValidationError:
            raise
            
        result = { "status": True }
        plugin_run = None
        if not dry_run:
            plugin_run = PluginRun.objects.create(
                video=video,
                type=plugin,
                status=PluginRun.STATUS_QUEUED,
            )
            # Exposed to callers (see views/plugin_run.py::PluginRunNew) so the frontend can
            # track/wait on this specific run without guessing which newly-appeared row is
            # "the" one -- needed e.g. to sequence team_clustering/osnet_reid after their
            # prerequisite object_tracker run finishes. Must be .hex (no dashes), matching
            # PluginRun.to_dict()'s "id" (self.id.hex, see models.py) -- that's the id format
            # /plugin/run/list actually keys pluginRunStore.state.pluginRuns by on the
            # frontend; str(plugin_run.id) here would produce dashed-UUID keys that never
            # match, so waitForDone() would wait on a key that's never populated.
            result["plugin_run_id"] = plugin_run.id.hex
            # Full entry so the frontend can drop the run straight into its store and
            # show it in the status list/badge immediately, without waiting for the
            # live event (and even if the event stream happens to be down).
            result["entry"] = plugin_run.to_dict()

        task_payload = {
            "plugin": plugin,
            "parameters": validated_parameters,
            "video": str(video.id),
            "user": str(user.id),
            "plugin_run": str(plugin_run.id) if plugin_run else None,
            "dry_run": dry_run,
            "kwargs": kwargs,
        }
        
        if run_async:
            task = run_plugin.apply_async(args=[task_payload])
            if plugin_run is not None:
                PluginRun.objects.filter(id=plugin_run.id).update(task_id=task.id)
            return result

        try:
            plugin_result = self._plugins[plugin]()(
                parameters,
                user=user,
                video=video,
                plugin_run=plugin_run,
                dry_run=dry_run,
                **kwargs,
            )
            if plugin_run is not None:
                plugin_run.progress = 1.0
                plugin_run.status = PluginRun.STATUS_DONE
                plugin_run.save()

            # creates cached files for all plugin run results
            manager = DataManager("/predictions/")

            generate_plugin_run_result_cache(
                manager, plugin_result.get("plugin_run_results", [])
            )
            if plugin_result: result["result"] = plugin_result

        except Exception:
            logger.exception(f"Failed to run plugin {plugin_run.type}")
            if plugin_run is not None:
                plugin_run.status = PluginRun.STATUS_ERROR
                plugin_run.save()
            result["status"] = False

        return result
    
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def get_results(self, analyse):
        if not hasattr(analyse, "type"):
            return None
        if analyse.type not in self._plugins:
            return None
        analyser = self._plugins[analyse.type]()
        if not hasattr(analyser, "get_results"):
            return {}
        return analyser.get_results(analyse)


def generate_plugin_run_result_cache(
    data_manager, plugin_run_result: List[str]
) -> None:
    for plugin_run_result_id in plugin_run_result:
        x = PluginRunResult.objects.get(id=plugin_run_result_id)
        cache_path = os.path.join(settings.DATA_CACHE_ROOT, f"{x.id}.json")
        cached = False
        try:
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    cached = True
        except Exception:
            logger.exception("Cache reading failed")
        if cached: continue

        data = data_manager.load(x.data_id)
        if data is None: continue

        with data:
            result_dict = {**x.to_dict(), "data": data.to_dict()}
            try:
                with open(cache_path, "w") as f:
                    json.dump(result_dict, f)
                    logger.debug(f"Writing result {x.id} to cache")
            except Exception:
                logger.exception("Cache couldn't write")


@shared_task(bind=True)
def run_plugin(self, args):
    plugin = args.get("plugin")
    parameters = args.get("parameters") or {}
    video = args.get("video")
    user = args.get("user")
    plugin_run = args.get("plugin_run")
    dry_run = args.get("dry_run")
    kwargs = args.get("kwargs") or {}

    video_db = Video.objects.get(id=video)
    user_db = SportVidUser.objects.get(id=user)
    
    plugin_run_db = None
    if not dry_run and plugin_run is not None:
        try:
            plugin_run_db = PluginRun.objects.get(id=plugin_run)
        except PluginRun.DoesNotExist:
            # Deleted (cancelled) before this task even got picked up -- e.g. it was
            # still queued behind other Celery tasks when the user hit delete. Nothing
            # to do or clean up: no analyser job was ever started for it.
            logger.info("PluginRun %s deleted before it started, skipping", plugin_run)
            return

        # Some plugins take another plugin_run's id as input (object_tracker_id for
        # team_clustering/osnet_reid, object_tracker_run_id for kpi_computation) and need that
        # run's *results*, not just its id -- submitting them while it's still QUEUED/RUNNING
        # crashes. The frontend (ModalPositionDataCreate.vue) submits Team Assignment/Re-ID
        # right alongside a freshly-started Object Tracker run rather than waiting around for
        # it client-side, so this reschedules itself via Celery's own retry until the
        # dependency is DONE (or gives up if it errors/never finishes). Checked *before* the
        # in_scheduler guard below on purpose: that flag is a one-shot "already picked up"
        # marker, so setting it first would make our own retry cancel itself the moment it
        # fires back up.
        dependency_id = next(
            (
                parameters[name]
                for name in ("object_tracker_id", "object_tracker_run_id")
                if parameters.get(name)
            ),
            None,
        )
        if dependency_id:
            dependency_run = PluginRun.objects.filter(id=dependency_id).first()
            if dependency_run is not None and dependency_run.status != PluginRun.STATUS_DONE:
                if dependency_run.status in (PluginRun.STATUS_ERROR, PluginRun.STATUS_UNKNOWN):
                    logger.error(
                        "Dependency plugin run %s (%s) didn't finish -- aborting %s",
                        dependency_id, dependency_run.status, plugin,
                    )
                    plugin_run_db.status = PluginRun.STATUS_ERROR
                    plugin_run_db.save()
                    return
                try:
                    # ~30 minutes total (360 * 5s) before giving up.
                    self.retry(countdown=5, max_retries=360)
                except MaxRetriesExceededError:
                    logger.error(
                        "Dependency plugin run %s never finished -- aborting %s",
                        dependency_id, plugin,
                    )
                    plugin_run_db.status = PluginRun.STATUS_ERROR
                    plugin_run_db.save()
                    return

        if plugin_run_db.in_scheduler:
            logger.warning("Job was rescheduled and will be canceled")
            return

        plugin_run_db.in_scheduler = True
        plugin_run_db.save()

    plugin_cls = PluginManager.get_plugin(plugin)
    if plugin_cls is None:
        logger.error("Plugin run failed: unknown plugin '%s'", plugin)
        if plugin_run_db is not None:
            plugin_run_db.status = PluginRun.STATUS_ERROR
            plugin_run_db.save()
        return
    
    try:
        plugin_result = plugin_cls()(
            parameters=parameters,
            user=user_db,
            video=video_db,
            plugin_run=plugin_run_db,
            dry_run=dry_run,
            **kwargs,
        )

        manager = DataManager("/predictions/")
        generate_plugin_run_result_cache(
            manager,
            plugin_result.get("plugin_run_results", []),
        )

        if plugin_run_db is not None:
            plugin_run_db.progress = 1.0
            plugin_run_db.status = PluginRun.STATUS_DONE
            plugin_run_db.save()

    except Exception:
        logger.exception("Plugin run failed for %s", plugin)
        if plugin_run_db is not None:
            plugin_run_db.status = PluginRun.STATUS_ERROR
            plugin_run_db.save()