import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class BackendConfig(AppConfig):
    name = "backend"

    def ready(self):
        # No database or Celery access here: ready() runs in every gunicorn worker and
        # Celery process. Unfinished runs are reconciled once at backend start by
        # `manage.py reconcile_plugin_runs` (backend/plugin_runs.py).

        # import django signal handlers
        import backend.signals  # noqa: F401

        # import serializers so their @PluginManager.export_serializer runs
        import backend.serializers  # noqa: F401

        # import the tasks so their @PluginManager.export_plugin runs, in every process
        import backend.tasks  # noqa: F401
