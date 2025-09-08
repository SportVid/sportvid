""" Django settings for the sportvid project.
    Run manage.py check --deploy to make sure this settings file is suited for a production environment.
"""

import os
import json
import logging

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENVIRONMENT = os.getenv('ENVIRONMENT')

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SECURE = True  # avoid transmitting CSRF cookie over HTTP
SESSION_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

if ENVIRONMENT == 'prod':
    CORS_ALLOWED_ORIGINS = [  # define allowed origins
        # "http://www.sportvid.dshs-koeln.de",
        # "http://sportvid.dshs-koeln.de",
        "https://www.sportvid.dshs-koeln.de",
        "https://sportvid.dshs-koeln.de"
    ]
elif ENVIRONMENT == 'dev':
    CORS_ALLOW_ALL_ORIGINS = True  # only use for debugging purpose

CORS_ALLOW_CREDENTIALS = True  # include cookies in cross-sitze HTTP requests

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
    # "root": {
    #     "handlers": ["console"],
    #     "level": "INFO",
    # },
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
]

AUTH_USER_MODEL = "backend.SportVidUser"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
        "NAME": os.getenv('DB_NAME'),
        "USER": os.getenv('DB_USER'),
        "PASSWORD": os.getenv('DB_PASSWORD'),
        "HOST": "postgres",
        "PORT": os.getenv('DB_PORT'),
    }
}

# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}
]

# https://docs.djangoproject.com/en/5.2/topics/i18n/
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATICFILES_DIRS = []

# last resolution is used for indexing
IMAGE_RESOLUTIONS = [{"min_dim": 200, "suffix": "_m"}, {"min_dim": 1080, "suffix": ""}]

GRPC_HOST = "analyser"
GRPC_PORT = 50051

MEDIA_URL = MEDIA_ROOT = "/media/"

DATA_CACHE_ROOT = "/cache/"

try: from .user_settings import * # type: ignore
except: pass

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
if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            for k, v in config_lut.items():
                if k in config:
                    globals()[v] = config[k]
    except Exception as e:
        logging.error("Failed to load or parse django settings file: {e}")
