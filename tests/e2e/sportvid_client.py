"""Minimaler HTTP-Client fuer die sportvid-API (Session-Login + CSRF).

Bildet nur die Endpunkte ab, die der E2E-Test braucht. Verhalten der
Endpunkte: siehe backend/src/backend/backend/views/{user,video,plugin,
plugin_run}.py (Stand deploy-dev).
"""

import json
import os
import time
from typing import Dict, List, Optional, Tuple

import requests


class ApiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class SportvidClient:
    def __init__(
        self,
        base_url: str,
        session: Optional[requests.Session] = None,
        basic_auth: Optional[Tuple[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api = f"{self.base_url}/api"
        self.session = session or requests.Session()
        # Die dev-Domain liegt komplett hinter nginx-Basic-Auth (proxy/nginx.conf,
        # auth_basic + .htpasswd; ausgenommen nur /api/login und /api/events/).
        # Ohne sie antwortet schon /api/user/csrf mit 401. Django selbst wertet den
        # Authorization-Header nicht aus (keine DRF-Views/-Auth-Klassen), es gibt
        # also keinen Konflikt mit dem Session-Login. requests schickt die
        # Credentials bei Redirects auf fremde Hosts nicht mit.
        if basic_auth:
            self.session.auth = basic_auth
        # Django prueft bei HTTPS-POSTs den Referer gegen CSRF_TRUSTED_ORIGINS.
        self.session.headers["Referer"] = f"{self.base_url}/"
        # Alle API-Antworten, die >= 500 waren - fuer das Pass/Fail-Kriterium
        # "keine 5xx der API-Aufrufe".
        self.server_errors: List[str] = []

    # --- intern -----------------------------------------------------------

    def _csrf_headers(self) -> Dict[str, str]:
        token = self.session.cookies.get("csrftoken")
        return {"X-CSRFToken": token} if token else {}

    def _handle(self, res: requests.Response, what: str) -> dict:
        if res.status_code >= 500:
            self.server_errors.append(f"{what}: HTTP {res.status_code}")
        try:
            body = res.json()
        except ValueError:
            raise ApiError(f"{what}: keine JSON-Antwort (HTTP {res.status_code})", res.status_code)
        if res.status_code >= 400 or body.get("status") != "ok":
            raise ApiError(f"{what}: {json.dumps(body)[:500]} (HTTP {res.status_code})", res.status_code)
        return body

    def _request(self, method: str, url: str, what: str, **kw) -> requests.Response:
        # Netzwerkfehler (Timeout, Connection refused) als ApiError, damit der
        # Lauf sauber als FAIL mit Report endet statt mit Traceback.
        try:
            return getattr(self.session, method)(url, **kw)
        except requests.RequestException as e:
            raise ApiError(f"{what}: Verbindungsfehler: {e}")

    def _get(self, path: str, what: str, **params) -> dict:
        res = self._request("get", f"{self.api}/{path}", what, params=params, timeout=60)
        return self._handle(res, what)

    def _post_json(self, path: str, what: str, payload: dict) -> dict:
        res = self._request(
            "post",
            f"{self.api}/{path}",
            what,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json", **self._csrf_headers()},
            timeout=60,
        )
        return self._handle(res, what)

    # --- Endpunkte ----------------------------------------------------------

    def login(self, username: str, password: str) -> None:
        # setzt das csrftoken-Cookie (ensure_csrf_cookie)
        self._get("user/csrf", "csrf")
        self._post_json("user/login", "login", {"params": {"name": username, "password": password}})

    def upload_video(self, path: str, title: str, fields: Dict[str, str]) -> str:
        with open(path, "rb") as fh:
            res = self._request(
                "post",
                f"{self.api}/video/upload",
                "video/upload",
                data={"title": title, **fields},
                files={"file": (os.path.basename(path), fh, "video/mp4")},
                headers=self._csrf_headers(),
                # Upload ueber den oeffentlichen Proxy kann dauern
                timeout=600,
            )
        body = self._handle(res, "video/upload")
        return body["entries"][0]["id"]

    def video_status(self, video_id: str) -> str:
        return self._get("video/get", "video/get", id=video_id)["entry"]["status"]

    def start_plugin(self, plugin: str, video_id: str, parameters: dict) -> str:
        body = self._post_json(
            "plugin/run/new",
            f"plugin/run/new {plugin}",
            {"plugin": plugin, "video_id": video_id, "parameters": parameters},
        )
        return body["plugin_run_id"]

    def plugin_runs(self, video_id: str) -> List[dict]:
        return self._get("plugin/run/list", "plugin/run/list", video_id=video_id)["entries"]

    def available_plugins(self) -> Optional[List[str]]:
        """Backend-Plugins, deren Ray-Plugins alle deployt sind (views/plugin.py).

        None = das Backend konnte den Analyser nicht fragen und nimmt dann jedes
        registrierte Plugin an.
        """
        return self._get("plugin/available", "plugin/available")["plugins"]

    def delete_video(self, video_id: str) -> None:
        # loescht per FK-CASCADE auch PluginRuns/Timelines des Videos
        self._post_json("video/delete", "video/delete", {"id": video_id})


def pin_host(hostname: str, ip: str) -> None:
    """Lenkt alle TCP-Verbindungen zu `hostname` auf `ip` (wie curl --resolve).

    Hairpin-Workaround fuer sportvid01 (siehe config.DEFAULT_CONNECT_IP).
    Nur der Socket-Aufbau wird umgebogen. Host-Header, TLS-SNI und
    Zertifikatspruefung nutzen weiter `hostname`, weil urllib3 diese getrennt
    vom Verbindungsziel setzt. Gilt prozessweit.
    """
    import urllib3.util.connection as conn

    original = conn.create_connection

    def create_connection(address, *args, **kwargs):
        host, port = address
        if host == hostname:
            address = (ip, port)
        return original(address, *args, **kwargs)

    conn.create_connection = create_connection


def wait_for(fn, done, failed, timeout: float, interval: float, what: str, sleep=time.sleep):
    """Pollt fn(), bis done(value) oder failed(value) gilt oder timeout ablaeuft."""
    deadline = time.monotonic() + timeout
    while True:
        value = fn()
        if done(value):
            return value
        if failed(value):
            raise ApiError(f"{what}: fehlgeschlagen ({value})")
        if time.monotonic() >= deadline:
            raise ApiError(f"{what}: Timeout nach {timeout:.0f}s (zuletzt {value})")
        sleep(interval)
