"""backend/utils/api.py: one place for authentication, JSON bodies and error status codes (T1, T13)."""
import ast
import json
import pathlib

import pytest
from django.http import JsonResponse
from django.test import RequestFactory
from django.urls import URLPattern, URLResolver

from backend.utils.api import ERROR_STATUS, LEGACY_ERROR_HEADER, ApiView, map_error_status

BACKEND = pathlib.Path(__file__).resolve().parents[2] / "backend/src/backend/backend"


def _status_of(body, status=200):
    response = map_error_status(JsonResponse(body, status=status))
    return response.status_code, response.get(LEGACY_ERROR_HEADER)


# ---------- mapping

@pytest.mark.parametrize("body, status, expected", [
    ({"status": "ok"}, 200, (200, None)),
    ({"status": "error", "type": "not_exist"}, 200, (404, "200")),
    ({"status": "error", "type": "missing_values"}, 200, (400, "200")),
    ({"status": "error", "type": "not_authenticated"}, 200, (401, "200")),
    ({"status": "error"}, 200, (500, "200")),                          # untyped: server error
    ({"status": "error_cluster_item_set_deleted"}, 200, (500, "200")),
    ({"status": "error", "type": "not_exist"}, 500, (404, None)),       # explicit code, known type
    ({"status": "error", "type": "file_too_large"}, 413, (413, None)),
    ({"status": "error"}, 403, (403, None)),                            # explicit code, untyped: kept
])
def test_error_status_mapping(body, status, expected):
    assert _status_of(body, status) == expected


def test_large_responses_are_not_parsed():
    body = {"status": "error", "padding": "x" * 5000}
    assert _status_of(body) == (200, None)


# ---------- ApiView

class _Echo(ApiView):
    def post(self, request):
        return JsonResponse({"status": "ok", "data": request.data})


class _Crash(ApiView):
    def get(self, request):
        raise RuntimeError("boom")


class _Strict(ApiView):
    legacy_errors = False

    def post(self, request):
        return JsonResponse({"status": "ok"})


@pytest.fixture
def user(db):
    from tests.factories import make_user
    return make_user()


def _post(view, user, body, content_type="application/json"):
    request = RequestFactory().post("/x", body, content_type=content_type)
    request.user = user
    return view.as_view()(request)


def test_json_body_is_parsed(user):
    response = _post(_Echo, user, json.dumps({"a": 1}))
    assert json.loads(response.content)["data"] == {"a": 1}


@pytest.mark.parametrize("body", ["{broken", "[1, 2]", "3"])
def test_body_that_is_not_a_json_object(user, body):
    response = _post(_Echo, user, body)
    assert response.status_code == 400
    assert json.loads(response.content)["type"] == "wrong_request_body"
    assert response[LEGACY_ERROR_HEADER] == "200"


def test_anonymous_request(db):
    from django.contrib.auth.models import AnonymousUser

    response = _post(_Echo, AnonymousUser(), "{}")
    assert (response.status_code, json.loads(response.content)["type"]) == (401, "not_authenticated")


def test_views_that_used_status_codes_get_no_legacy_marker(db):
    from django.contrib.auth.models import AnonymousUser

    response = _post(_Strict, AnonymousUser(), "{}")
    assert response.status_code == 401
    assert LEGACY_ERROR_HEADER not in response


def test_uncaught_exception_is_a_500(user):
    request = RequestFactory().get("/x")
    request.user = user
    response = _Crash.as_view()(request)
    assert (response.status_code, json.loads(response.content)) == (500, {"status": "error", "type": "internal_error"})


# ---------- guards: every view goes through the wrapper, every error type has a status

def _patterns(resolver_patterns, prefix=""):
    for p in resolver_patterns:
        if isinstance(p, URLResolver):
            yield from _patterns(p.url_patterns, prefix + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield prefix + str(p.pattern), p.callback


PUBLIC_WITHOUT_WRAPPER = {"user/csrf"}  # only sets the CSRF cookie


def test_every_api_route_uses_the_wrapper():
    from backend.urls import urlpatterns

    missing = []
    for path, callback in _patterns(urlpatterns):
        view_class = getattr(callback, "view_class", None)
        if view_class is not None and issubclass(view_class, ApiView):
            continue
        if getattr(callback, "is_api_view", False) or path in PUBLIC_WITHOUT_WRAPPER:
            continue
        missing.append(path)
    assert missing == []


def test_no_view_checks_authentication_inline():
    """T1: the check lives in ApiView/api_function only."""
    offenders = []
    for path in sorted((BACKEND / "views").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.If, ast.IfExp)) and "is_authenticated" in ast.dump(node.test):
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


def _error_types():
    for path in [*(BACKEND / "views").glob("*.py"), BACKEND / "utils/upload.py"]:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Dict):
                fields = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
                status, error_type = fields.get("status"), fields.get("type")
                if isinstance(status, ast.Constant) and status.value == "error" and isinstance(error_type, ast.Constant):
                    yield f"{path.name}:{node.lineno}", error_type.value


def test_every_error_type_has_a_status_code():
    assert [(where, t) for where, t in _error_types() if t not in ERROR_STATUS] == []
