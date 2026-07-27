""" Django settings for the sportvid project.
    Run manage.py check --deploy to make sure this settings file is suited for a production environment.
"""
import os
import json
import logging
from celery.schedules import crontab

# build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
CORS_ALLOW_CREDENTIALS = True

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # NOTE: True?
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s][%(levelname)s][%(name)s.%(funcName)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    # NOTE: comment in "root" logger to see stack trace.
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "backend": {
            "handlers": ["console"], 
            "level": "INFO", 
            "propagate": False  # NOTE: True?
        },
        "django": {
            "handlers": ["console"], 
            "level": "WARNING", 
            "propagate": False  # NOTE: True?
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "backend",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_beat",
]

AUTH_USER_MODEL = "backend.SportVidUser"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # "mozilla_django_oidc.middleware.SessionRefresh",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sportvid.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sportvid.wsgi.application"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": "memcached:11211",
        "TIMEOUT": 60 * 60 * 24,
    }
}

# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "sportvid",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "postgres",
        "PORT": 5432,
    }
}

# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}
]

# Celery beat (crontab)
# TODO: not detecting task, fix this....
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
# CELERY_BEAT_SCHEDULE = {
#     'cleanup-orphans': {
#         'task': 'tibava.backend.tasks.convert_video.cleanup_upload_orphans',
#         'schedule': crontab(hour='*/1'),  # hourly schedule for cleanup
#     },
# }

# Celery beat (crontab)
# TODO: not detecting task, fix this....
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
# CELERY_BEAT_SCHEDULE = {
#     'cleanup-orphans': {
#         'task': 'tibava.backend.tasks.convert_video.cleanup_upload_orphans',
#         'schedule': crontab(hour='*/1'),  # hourly schedule for cleanup
#     },
# }

# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATICFILES_DIRS = []

# last resolution is used for indexing
IMAGE_RESOLUTIONS = [{"min_dim": 200, "suffix": "_m"}, {"min_dim": 1080, "suffix": ""}]

try: from .user_settings import *
except: pass

MEDIA_URL = "/media/"
THUMBNAIL_URL = "http://localhost/thumbnails/"

# the last resolution will use for indexing
IMAGE_RESOLUTIONS = [{"min_dim": 200, "suffix": "_m"}, {"min_dim": 1080, "suffix": ""}]

# FILE_UPLOAD_HANDLERS = [
#    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
#    'django.core.files.uploadhandler.MemoryFileUploadHandler',
# ]
# DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB threshold

import json

config_lut = {
    "secret_key": "SECRET_KEY",
    "force_script_name": "FORCE_SCRIPT_NAME",
    "allowed_hosts": "ALLOWED_HOSTS",
    "csrf_trusted_origins": "CSRF_TRUSTED_ORIGINS",
    "debug": "DEBUG",
    "language_code": "LANGUAGE_CODE",
    "static_url": "STATIC_URL",
    "media_root": "MEDIA_ROOT",
    "data_cache_root": "DATA_CACHE_ROOT",
    "data_output_path": "DATA_OUTPUT_PATH",
    "upload_root": "UPLOAD_ROOT",
    "upload_url": "UPLOAD_URL",
    "media_url": "MEDIA_URL",
    "upload_url": "UPLOAD_URL",
    "data_cache_root": "DATA_CACHE_ROOT",
    "data_path": "DATA_PATH",
    "indexer_path": "INDEXER_PATH",
    "thumbnail_url": "THUMBNAIL_URL",
    "grpc_host": "GRPC_HOST",
    "grpc_port": "GRPC_PORT",
    "image_resolutions": "IMAGE_RESOLUTIONS",
    "pipelines": "PIPELINES",
    "annotation_max_length": "ANNOTATION_MAX_LENGTH"
}

config_path = "/run/secrets/django_settings"

# logging.error(f"SETTINGS FILE: {__file__}")
# logging.error(f"SECRET EXISTS: {os.path.exists(config_path)}")
# logging.error(f"MEDIA_ROOT BEFORE LOAD: {repr(globals().get('MEDIA_ROOT'))}")

if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            for k, v in config_lut.items():
                if k in config:
                    globals()[v] = config[k]
        logging.error(f"Successfully parsed django settings file: {config_path}")
    except Exception as e:
        logging.error(f"Failed to load or parse django settings file: {e}")

# logging.error(f"MEDIA_ROOT AFTER LOAD: {repr(globals().get('MEDIA_ROOT'))}")