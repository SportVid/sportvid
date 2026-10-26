"""Characterization: what local development needs from sportvid/settings.py.

settings.py runs at import time, so each case imports it in a fresh interpreter with a
controlled environment (the values below are the ones in the tracked .env).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[2] / "backend" / "src" / "backend"

LOCAL_ENV = {
    "ENVIRONMENT": "local",
    "POSTGRES_DB": "sportvid",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "DB_PORT": "5432",
    "VALKEY_CLIENT_HOST": "valkey",
    "VALKEY_INTERNAL_PORT": "6380",
}

PROBE = """
import json, sportvid.settings as s
print(json.dumps({
    "db": {k: s.DATABASES["default"][k] for k in ("NAME", "USER", "PASSWORD", "HOST", "PORT")},
    "session_secure": s.SESSION_COOKIE_SECURE, "csrf_secure": s.CSRF_COOKIE_SECURE,
    "allowed_hosts": s.ALLOWED_HOSTS, "cors": s.CORS_ALLOWED_ORIGINS, "csrf_trusted": s.CSRF_TRUSTED_ORIGINS,
}))
"""


def load_settings(env, extra_code=""):
    full_env = {k: v for k, v in os.environ.items() if k not in LOCAL_ENV and not k.startswith(("DB_", "POSTGRES_", "VALKEY_", "DJANGO_"))}
    full_env.update(env)
    result = subprocess.run(
        [sys.executable, "-c", PROBE + extra_code], cwd=BACKEND_SRC, env=full_env, capture_output=True, text=True
    )
    return result


def test_local_development_settings():
    result = load_settings(LOCAL_ENV)
    assert result.returncode == 0, result.stderr
    s = json.loads(result.stdout.strip().splitlines()[-1])
    assert s["db"] == {"NAME": "sportvid", "USER": "postgres", "PASSWORD": "postgres", "HOST": "postgres", "PORT": 5432} or \
        s["db"] == {"NAME": "sportvid", "USER": "postgres", "PASSWORD": "postgres", "HOST": "postgres", "PORT": "5432"}
    assert (s["session_secure"], s["csrf_secure"]) == (False, False)  # local runs over plain HTTP
    assert {"localhost", "127.0.0.1", "backend"} <= set(s["allowed_hosts"])
    assert "http://localhost:8080" in s["cors"] and "http://localhost:8080" in s["csrf_trusted"]
