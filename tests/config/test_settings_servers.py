"""Settings fail closed on the servers (ENVIRONMENT dev/prod/unset) and read everything from env."""
import json

import pytest

from .test_settings_local import LOCAL_ENV, load_settings

GOOD_SECRET = {"secret_key": "k" * 20 + "0123456789abcdefghijklmnopqrstuvwxyz", "debug": False,
               "public_base_url": "https://dev.sportvid.dshs-koeln.de/"}
SERVER_ENV = {"ENVIRONMENT": "dev", "DB_NAME": "sv", "DB_USER": "u", "DB_PASSWORD": "p", "DB_PORT": "5433",
              "VALKEY_CLIENT_HOST": "valkey", "VALKEY_INTERNAL_PORT": "6380", "VALKEY_PASSWD": "v@l/key"}

PROBE_SERVER = """
import sportvid.settings as s, sportvid.celery as c
print(json.dumps({"secure": [s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, s.SECURE_SSL_REDIRECT, s.SECURE_HSTS_SECONDS],
                  "db": [s.DATABASES["default"][k] for k in ("NAME", "USER", "PASSWORD", "PORT")],
                  "valkey": s.VALKEY_PASSWORD, "broker": c.app.conf.broker_url, "base": s.PUBLIC_BASE_URL,
                  "thumbs": s.THUMBNAIL_URL, "cors": s.CORS_ALLOWED_ORIGINS}))
"""


def with_secret(tmp_path, env, secret):
    path = tmp_path / "secret.json"
    path.write_text(secret if isinstance(secret, str) else json.dumps(secret))
    return {**env, "DJANGO_SETTINGS_SECRET": str(path)}


def last_json(result):
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_server_settings_come_from_env_and_secret(tmp_path):
    result = load_settings(with_secret(tmp_path, SERVER_ENV, GOOD_SECRET), PROBE_SERVER)
    assert result.returncode == 0, result.stderr
    s = last_json(result)
    assert s["secure"] == [True, True, True, 31536000]
    assert s["db"] == ["sv", "u", "p", "5433"]
    assert s["valkey"] == "v@l/key"
    assert s["broker"].startswith("redis://:v%40l%2Fkey@valkey:6380/")  # password URL-quoted
    assert (s["base"], s["thumbs"]) == ("https://dev.sportvid.dshs-koeln.de", "https://dev.sportvid.dshs-koeln.de/thumbnails/")
    assert s["cors"] == ["https://www.dev.sportvid.dshs-koeln.de", "https://dev.sportvid.dshs-koeln.de"]


@pytest.mark.parametrize("change, message", [
    ({"secret_key": "SECRET_KEY"}, "secret_key"),
    ({"secret_key": "default-secret"}, "secret_key"),
    ({"debug": True}, "debug"),
    ({"public_base_url": "http://localhost"}, "public_base_url"),
])
def test_server_refuses_unsafe_secret(tmp_path, change, message):
    result = load_settings(with_secret(tmp_path, SERVER_ENV, {**GOOD_SECRET, **change}))
    assert result.returncode != 0 and "ImproperlyConfigured" in result.stderr and message in result.stderr


@pytest.mark.parametrize("missing", ["DB_PASSWORD", "VALKEY_PASSWD"])
def test_server_refuses_missing_credentials(tmp_path, missing):
    env = {k: v for k, v in SERVER_ENV.items() if k != missing}
    result = load_settings(with_secret(tmp_path, env, GOOD_SECRET))
    assert result.returncode != 0 and missing in result.stderr


def test_unset_environment_is_treated_like_a_server(tmp_path):
    env = {k: v for k, v in LOCAL_ENV.items() if k != "ENVIRONMENT"}
    result = load_settings(env)
    assert result.returncode != 0 and "Refusing to start" in result.stderr


def test_broken_secret_stops_startup_even_locally(tmp_path):
    result = load_settings(with_secret(tmp_path, LOCAL_ENV, "{not json"))
    assert result.returncode != 0 and "Cannot read the settings secret" in result.stderr


def test_local_stack_with_tracked_dev_secret(tmp_path):
    tracked = json.load(open("config/backend.json"))
    result = load_settings(with_secret(tmp_path, LOCAL_ENV, tracked))
    assert result.returncode == 0, result.stderr
