import json
import logging

from functools import wraps

from django.http import JsonResponse


logger = logging.getLogger(__name__)


def decode_and_authenticate(require_name=True):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            try:
                if not request.user.is_authenticated:
                    return JsonResponse({"status": "error", "type": "not_authenticated"})
                
                try:
                    body = request.body.decode("utf-8")
                except (UnicodeDecodeError, AttributeError):
                    body = request.body

                try:
                    data = json.loads(body)
                except Exception:
                    return JsonResponse({"status": "error", "type": "wrong_request_body"})

                if require_name and "name" not in data:
                    return JsonResponse({"status": "error", "type": "missing_values"})

                return view_func(self, request, data, *args, **kwargs)
            except Exception:
                logger.exception(f'Failed in {view_func.__name__}')
                return JsonResponse({"status": "error"})
        return wrapper
    return decorator