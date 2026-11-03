"""Django settings for the test suite: production settings with local, isolated services."""
import os
import tempfile

# Same environment as the local stack's .env; settings fail closed without it.
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("POSTGRES_DB", "sportvid")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")

from sportvid.settings import *  # noqa: E402,F401,F403

SECRET_KEY = "test-only-not-a-secret"
DEBUG = False

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# All file-system roots point into a throwaway directory.
TEST_DATA_ROOT = tempfile.mkdtemp(prefix="sportvid-tests-")
MEDIA_ROOT = f"{TEST_DATA_ROOT}/media/"
DATA_OUTPUT_PATH = f"{TEST_DATA_ROOT}/predictions/"
DATA_CACHE_ROOT = f"{TEST_DATA_ROOT}/cache/"
UPLOAD_ROOT = f"{TEST_DATA_ROOT}/upload/"
