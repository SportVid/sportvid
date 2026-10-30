"""request_id: one ID on every log line of an API request and of the Celery tasks it enqueues."""
import json
import re

import pytest
from celery import Celery
from celery.contrib.testing.worker import start_worker

from backend.log_context import current, log_context
from tests.factories import make_user, make_video


def test_a_request_gets_an_id(client):
    r = client.get("/healthy/")
    assert re.fullmatch(r"[0-9a-f]{32}", r["X-Request-ID"])
    assert client.get("/healthy/")["X-Request-ID"] != r["X-Request-ID"]


def test_the_proxys_id_is_kept(client):
    r = client.get("/healthy/", HTTP_X_REQUEST_ID="0f3c9e2a7b1d4e5f8a9b0c1d2e3f4a5b")
    assert r["X-Request-ID"] == "0f3c9e2a7b1d4e5f8a9b0c1d2e3f4a5b"


@pytest.mark.parametrize("incoming", ['id" injected=1', "x" * 65, "id\n"], ids=["characters", "length", "trailing_newline"])
def test_ids_that_could_garble_the_log_are_replaced(client, incoming):
    r = client.get("/healthy/", HTTP_X_REQUEST_ID=incoming)
    assert re.fullmatch(r"[0-9a-f]{32}", r["X-Request-ID"])


def test_the_requests_log_lines_carry_it(client, db, log_lines, cancel_messages):
    user = make_user("alice")
    client.force_login(user)
    video = make_video(user)

    r = client.post("/video/delete", json.dumps({"id": video.id.hex}), content_type="application/json",
                    HTTP_X_REQUEST_ID="req-1")

    assert r["X-Request-ID"] == "req-1"
    assert any(line.startswith("INFO video.delete request_id=req-1 ") for line in log_lines())
    assert current() == {}  # nothing left bound after the request


@pytest.fixture(scope="module")
def worker():
    """A real Celery worker (thread pool, like production) on an in-memory broker.

    The request_id hooks are Celery signals, connected for every app by importing sportvid.celery.
    Module-scoped: stopping it takes ~4 s (Celery's synloop drains with a fixed 2 s timeout).
    """
    import sportvid.celery  # noqa: F401

    app = Celery("request-id-test", broker="memory://", backend="cache+memory://")
    app.conf.broker_transport_options = {"polling_interval": 0.01}  # default 1 s per message

    @app.task
    def bound_request_id():
        return current().get("request_id")

    with start_worker(app, pool="threads", concurrency=1, perform_ping_check=False, loglevel="WARNING"):
        yield bound_request_id


def test_a_task_enqueued_by_a_request_logs_its_id(worker):
    with log_context(request_id="req-1"):
        result = worker.delay()
    assert result.get(timeout=10, interval=0.01) == "req-1"


def test_the_worker_thread_forgets_it_after_the_task(worker):
    with log_context(request_id="req-1"):
        worker.delay().get(timeout=10, interval=0.01)
    # same worker thread (concurrency=1), task enqueued outside any request
    assert worker.delay().get(timeout=10, interval=0.01) is None
