import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sportvid.settings")

# set broker URL accordingly
broker_url = f"redis://valkey:{os.getenv('VALKEY_PORT')}"

app = Celery("sportvid", 
             broker=broker_url
) # type: ignore

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# if ENVIRONMENT == 'production':
#     app.conf.update(
#         task_serializer='json',
#         accept_content=['json'],
#         result_serializer='json',
#         result_expires=3600,
#         enable_utc=True,
#         timezone='Europe/Berlin',
#         task_soft_time_limit=30,
#         task_time_limit=120,
#         worker_prefetch_multiplier=4,
#         task_acks_late=False,
#         worker_disable_rate_limits=False,
#     )
# else:
#     app.conf.update(
#         task_always_eager=True,  # sync execution
#         task_eager_propagates=True,
#         worker_prefetch_multiplier=1,
#         task_acks_late=False,
#     )

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
