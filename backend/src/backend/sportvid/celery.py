import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sportvid.settings")

# set broker URL accordingly
valkey_host = os.getenv("VALKEY_CLIENT_HOST")  # "valkey"
valkey_port = os.getenv("VALKEY_INTERNAL_PORT")  # "6380"
valkey_passwd = os.getenv("VALKEY_PASSWD")

broker_url = f"redis://:{valkey_passwd}@{valkey_host}:{valkey_port}/0"

app = Celery("sportvid", broker=broker_url) # type: ignore

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

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
