import logging
import traceback
import sys
import os
import json
from celery import shared_task
from django.conf import settings
from typing import Any, Dict, List, Optional, Type
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

    @classmethod
    def validate_parameters(cls, plugin: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        parameters = parameters or {}
        logging.error(parameters)

        serializer_cls = cls.get_serializer(plugin)
        if serializer_cls is None:
            return parameters

        serializer = serializer_cls(data=parameters or {})
        serializer.is_valid(raise_exception=True)
        return dict(serializer.validated_data)

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
            run_plugin.apply_async(args=[task_payload])
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
                    logger.debug(f"Writin result {x.id} to cache")
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
        plugin_run_db = PluginRun.objects.get(id=plugin_run)
        
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