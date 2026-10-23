"""B7: state-changing requests need the CSRF token, as the frontend sends it.

The frontend first GETs user/csrf (sets the csrftoken cookie), then sends the cookie's
value as X-CSRFToken on every request (frontend/src/plugins/axios.js).
"""
import json

import pytest
from django.test import Client

from backend.models import SportVidUser, Timeline


@pytest.fixture
def browser():
    return Client(enforce_csrf_checks=True)


def token(client):
    return client.cookies["csrftoken"].value


def post_json(client, path, payload, with_token=True):
    headers = {"HTTP_X_CSRFTOKEN": token(client)} if with_token else {}
    return client.post(path, json.dumps(payload), content_type="application/json", **headers)


def login(browser, world):
    browser.get("/user/csrf")
    response = post_json(browser, "/user/login", {"params": {"name": "alice", "password": "pw"}})
    assert response.json()["status"] == "ok"


def test_csrf_endpoint_sets_the_cookie(browser):
    browser.get("/user/csrf")
    assert token(browser)


def test_login_and_write_with_token(browser, world):
    login(browser, world)  # Django rotates the token on login; token() reads the new cookie
    response = post_json(browser, "/timeline/create", {"video_id": world.video.id.hex, "name": "t"})
    assert response.json()["status"] == "ok"


def test_write_without_token_is_rejected(browser, world):
    login(browser, world)
    before = Timeline.objects.count()
    response = post_json(browser, "/timeline/create", {"video_id": world.video.id.hex, "name": "t"}, with_token=False)
    assert response.status_code == 403
    assert Timeline.objects.count() == before


def test_cross_site_form_post_cannot_change_a_logged_in_users_account(browser, world):
    login(browser, world)
    response = browser.post("/user/update", {"params": "x"})  # no token, as a foreign site would send
    assert response.status_code == 403
    assert SportVidUser.objects.get(username="alice").email == "alice@example.org"


def test_login_without_token_is_rejected(browser, world):
    browser.get("/user/csrf")
    response = post_json(browser, "/user/login", {"params": {"name": "alice", "password": "pw"}}, with_token=False)
    assert response.status_code == 403
