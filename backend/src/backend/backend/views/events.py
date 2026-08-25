import logging

from django.db import connection
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View

from backend.utils.events import subscribe

logger = logging.getLogger(__name__)


class EventStream(View):
    """Server-sent events for the logged-in user (plugin run + video state changes).

    Replaces the frontend's polling loops: the browser holds one connection open and
    the backend pushes whenever something actually changed.
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"status": "error"}, status=401)

        response = StreamingHttpResponse(
            self._stream(request.user.id),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        # Tell nginx not to buffer -- otherwise events pile up until the buffer flushes.
        response["X-Accel-Buffering"] = "no"
        return response

    @staticmethod
    def _stream(user_id):
        # A stream lives for minutes; holding this thread's database connection open
        # for all of it would tie up a postgres backend for nothing.
        connection.close()
        try:
            yield from subscribe(user_id)
        except GeneratorExit:
            raise
        except Exception:
            logger.warning("Event stream for user %s ended unexpectedly", user_id, exc_info=True)
