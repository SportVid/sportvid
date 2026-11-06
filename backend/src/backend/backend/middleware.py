import re
import uuid

from backend.log_context import log_context

# What a proxy's request ID looks like (nginx's $request_id is 32 hex chars). Anything else
# is replaced, so a client can't write arbitrary text into the log lines.
_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


class RequestIdMiddleware:
    """Binds a request ID to every log line of the request and returns it as X-Request-ID.

    The ID comes from the incoming X-Request-ID header when it looks like one, otherwise it
    is generated. Celery tasks enqueued during the request carry it on (sportvid/celery.py),
    so `grep request_id=<id>` finds an upload together with its conversion. Lines of a
    streamed response (SSE) are written after this returns and don't carry it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request.request_id = incoming if _REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        with log_context(request_id=request.request_id):
            response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response
