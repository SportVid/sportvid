import os
from urllib.parse import quote
from celery import Celery
from celery.signals import before_task_publish, task_postrun, task_prerun

from backend.log_context import bind, current, unbind

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sportvid.settings")


def _broker_url():
    """Valkey broker from the environment (same variables as sportvid.settings)."""
    host = os.getenv("VALKEY_CLIENT_HOST", "valkey")
    port = os.getenv("VALKEY_INTERNAL_PORT", "6380")
    password = os.getenv("VALKEY_PASSWD")
    auth = f":{quote(password, safe='')}@" if password else ""
    return f"redis://{auth}{host}:{port}/0"


app = Celery("sportvid", broker=_broker_url())

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


# The request_id of the API request (backend.middleware.RequestIdMiddleware) that enqueued a
# task travels as a message header and is bound to the task's log lines. A header, not an
# argument: task signatures stay as they are, and workers of an older release ignore it.
REQUEST_ID_HEADER = "sportvid_request_id"
_bound = {}  # task id -> contextvar token; prerun and postrun run on the task's thread


@before_task_publish.connect
def _send_request_id(headers=None, **kwargs):
    request_id = current().get("request_id")
    if request_id and headers is not None:
        headers.setdefault(REQUEST_ID_HEADER, request_id)


@task_prerun.connect
def _bind_request_id(task_id=None, task=None, **kwargs):
    request_id = task.request.get(REQUEST_ID_HEADER) if task is not None else None
    if request_id:
        _bound[task_id] = bind(request_id=request_id)


@task_postrun.connect
def _unbind_request_id(task_id=None, **kwargs):
    token = _bound.pop(task_id, None)
    if token is not None:
        try:
            unbind(token)
        except ValueError:  # bound in another context; nothing to undo here
            pass
