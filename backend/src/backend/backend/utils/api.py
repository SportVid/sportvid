"""Authentication, JSON bodies and error status codes for every API view, in one place.

ADR 0005 (decisions 2 and 3), rules T1 and T13. A view subclasses `ApiView` instead of
`django.views.View` and gets:

- login required (401 `not_authenticated`), unless the class sets `public = True`;
- for POST, the JSON body as `request.data` (400 `wrong_request_body` if it isn't a JSON
  object); upload and form views set `json_body = False` and read `request.POST`/`FILES`;
- an uncaught exception answers 500 `internal_error` and is logged;
- every error response `{"status": "error", "type": ...}` gets the status code that
  ERROR_STATUS gives its type; errors without a type are server errors (500).

Function views use the `api_function` decorator, which does the same.
"""
import json
import logging
from functools import wraps

from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)

ERROR_STATUS = {
    # the request is malformed or invalid
    **dict.fromkeys([
        "wrong_request_body", "validation_error", "wrong_type", "wrong_value", "unknown_format",
        "missing_values", "missing_values_cluster_id", "missing_values_plugin_item_ref_list",
        "missing_values_plugin_list", "missing_args", "missing_params", "Params missing",
        "weak_password", "invalid_password", "user_exists", "wrong_file_extension",
        "plugin_unavailable", "exist",
        "not_calibrated", "wrong_direction", "unsupported_lens_profile",
        "incompatible_resolution", "invalid_lens_crop",
    ], 400),
    **dict.fromkeys(["not_authenticated", "user_auth", "invalid_credentials"], 401),
    **dict.fromkeys(["not_authorized", "not_approved"], 403),
    **dict.fromkeys(["not_exist", "not_found", "video_not_found", "file_not_found"], 404),
    **dict.fromkeys(["file_too_large", "quota_exceeded"], 413),
    **dict.fromkeys([
        "internal_error", "database_error", "dataload", "data_load", "downloading_error",
        "plugin_not_started", "delete_op", "general",
    ], 500),
}

# Set on an error that answered HTTP 200 before T13. The frontend's axios instance hands
# such responses to the stores as before (frontend/src/plugins/axios.js); remove both once
# every store handles real status codes (docs/todos/FRONTEND.md).
LEGACY_ERROR_HEADER = "X-Legacy-Error-Status"

# Error bodies are small; larger responses are never parsed.
_MAX_ERROR_BODY = 4096


def error_response(error_type, legacy=False, **fields):
    """An error response with the status code of its type."""
    response = JsonResponse({"status": "error", "type": error_type, **fields}, status=ERROR_STATUS.get(error_type, 400))
    if legacy:
        response[LEGACY_ERROR_HEADER] = "200"
    return response


def map_error_status(response):
    """Give an error JsonResponse the status code of its type (T13).

    The status a view set explicitly is replaced only for a known type. An error that was
    HTTP 200 is marked with LEGACY_ERROR_HEADER.
    """
    if not isinstance(response, JsonResponse) or len(response.content) > _MAX_ERROR_BODY:
        return response
    try:
        body = json.loads(response.content)
    except ValueError:
        return response
    if not isinstance(body, dict) or not str(body.get("status", "")).startswith("error"):
        return response

    error_type = body.get("type") if body.get("status") == "error" else None
    if error_type in ERROR_STATUS:
        status = ERROR_STATUS[error_type]
    elif error_type is not None:
        status = response.status_code if response.status_code >= 400 else 400
    else:
        status = response.status_code if response.status_code >= 400 else 500
    if response.status_code < 400:
        response[LEGACY_ERROR_HEADER] = str(response.status_code)
    response.status_code = status
    return response


def parse_json_object(body):
    """The request body as a dict ({} when empty), or None if it isn't a JSON object."""
    if not body:
        return {}
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _handle(request, public, json_body, legacy_errors, call, name):
    if not public and not request.user.is_authenticated:
        return error_response("not_authenticated", legacy=legacy_errors)
    if request.method == "POST" and json_body:
        data = parse_json_object(request.body)
        if data is None:
            return error_response("wrong_request_body", legacy=legacy_errors)
        request.data = data
    try:
        response = call()
    except Exception:
        logger.exception("Unhandled error in %s", name)
        return error_response("internal_error")
    return map_error_status(response)


class ApiView(View):
    """Base class of the API views; see the module docstring."""

    public = False
    json_body = True
    # Most views answered "not logged in" and broken JSON with HTTP 200, so these errors are
    # legacy-marked. Views that already used error status codes for them set False.
    legacy_errors = True

    def dispatch(self, request, *args, **kwargs):
        return _handle(
            request, self.public, self.json_body, self.legacy_errors,
            lambda: super(ApiView, self).dispatch(request, *args, **kwargs), type(self).__name__,
        )


def api_function(public=False, json_body=True, legacy_errors=True):
    """ApiView's handling for a function view."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return _handle(
                request, public, json_body, legacy_errors,
                lambda: view_func(request, *args, **kwargs), view_func.__name__,
            )
        wrapper.is_api_view = True  # copied by functools.wraps of outer decorators; see tests/api
        return wrapper
    return decorator
