import logging
import sys

from django.apps import AppConfig
from django.db.models import Q
from django.db import connection


logger = logging.getLogger(__name__)

# Schema-management commands run django.setup() -- and therefore ready() -- before the
# DB is necessarily in sync with the current models (that's the whole point of running
# them). The startup query below assumes every model field already has a matching
# column, which isn't true yet e.g. while a migration for a new field hasn't been
# created/applied. See Django's own "Accessing the database during app initialization
# is discouraged" warning.
_SCHEMA_COMMANDS = {"makemigrations", "migrate", "showmigrations", "sqlmigrate", "squashmigrations"}


class BackendConfig(AppConfig):
    name = "backend"

    def ready(self):
        # Registered before the table check below -- on a fresh database that check
        # returns early, and the live-event signals would silently never be connected.
        import backend.signals  # noqa: F401

        if _SCHEMA_COMMANDS.intersection(sys.argv):
            return

        if 'backend_pluginrun' not in connection.introspection.table_names():
            return
        # import here otherwise django complains
        from sportvid.celery import app
        from backend.models import PluginRun
        
        # import serializers for auto discovery
        import backend.serializers

        # set unfinished tasks to ERROR on startup
        inspect = app.control.inspect()

        scheduled = inspect.scheduled()
        active = inspect.active()
        reserved = inspect.reserved()

        # inspect can return None or dict
        if scheduled is None or active is None or reserved is None:
            return

        celery_runs = [
            run['args'][0]['plugin_run']
            for category in (list(scheduled.values()) +
                             list(active.values()) +
                             list(reserved.values()))
            for run in category
        ]

        open_runs = PluginRun.objects.exclude(Q(status=PluginRun.STATUS_DONE)|
                                              Q(status=PluginRun.STATUS_ERROR)|
                                              Q(id__in=celery_runs))
        if len(open_runs) > 0:
            logger.warning(
                f'Setting the status of {len(open_runs)} non-running PluginRuns to UNKNOWN'
            )
            open_runs.update(status=PluginRun.STATUS_UNKNOWN)
