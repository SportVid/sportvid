"""S3: password rules, admin approval of new accounts, and the account commands."""
import json

import pytest
from django.core.management import CommandError, call_command

from backend.models import SportVidUser

STRONG = "Correct-Horse-Battery-42"


def post(client, path, params):
    return client.post(path, json.dumps({"params": params}), content_type="application/json")


@pytest.fixture
def admin(db):
    user = SportVidUser.objects.create_user("adam", "adam@example.org", STRONG)
    user.role = "admin"
    user.save()
    return user


# ---------- registration
@pytest.mark.parametrize("password", ["12345678", "password", "short", "newbie2026"])
def test_register_rejects_weak_passwords(client, db, password):
    r = post(client, "/user/register", {"name": "newbie2026", "password": password, "email": "n@example.org"})
    assert r.json()["status"] == "error" and r.json()["type"] == "weak_password"
    assert not SportVidUser.objects.filter(username="newbie2026").exists()


def test_register_creates_an_inactive_account_and_does_not_log_in(client, db):
    r = post(client, "/user/register", {"name": "newbie", "password": STRONG, "email": "n@example.org"})
    assert r.json() == {"status": "ok", "pending_approval": True}
    assert SportVidUser.objects.get(username="newbie").is_active is False
    assert client.post("/user/get").status_code == 401


def test_pending_account_is_told_only_with_the_right_password(client, db):
    post(client, "/user/register", {"name": "newbie", "password": STRONG, "email": "n@example.org"})
    assert post(client, "/user/login", {"name": "newbie", "password": STRONG}).json()["type"] == "not_approved"
    assert post(client, "/user/login", {"name": "newbie", "password": "wrong"}).json() == {
        "status": "error", "message": "Invalid login credentials"}


def test_admin_approval_enables_login(client, db, admin):
    post(client, "/user/register", {"name": "newbie", "password": STRONG, "email": "n@example.org"})
    newbie = SportVidUser.objects.get(username="newbie")
    client.force_login(admin)
    r = post(client, "/user/update", {"update_type": "admin", "id": newbie.id, "is_active": True})
    assert r.json()["status"] == "ok" and r.json()["data"]["is_active"] is True
    assert {"date_joined", "is_active"} <= set(r.json()["data"])
    client.logout()
    assert post(client, "/user/login", {"name": "newbie", "password": STRONG}).json()["status"] == "ok"


def test_admin_cannot_deactivate_themselves(client, admin):
    client.force_login(admin)
    r = post(client, "/user/update", {"update_type": "admin", "id": admin.id, "is_active": False})
    assert r.json()["status"] == "error"
    admin.refresh_from_db()
    assert admin.is_active


def test_is_active_must_be_a_boolean(client, admin, db):
    other = SportVidUser.objects.create_user("bob", "b@example.org", STRONG)
    client.force_login(admin)
    assert post(client, "/user/update", {"update_type": "admin", "id": other.id, "is_active": "yes"}).json()["status"] == "error"


def test_existing_accounts_stay_active(db):
    assert SportVidUser.objects.create_user("legacy", "l@example.org", STRONG).is_active


# ---------- password change
def test_password_change_rejects_weak_passwords(client, db):
    user = SportVidUser.objects.create_user("alice", "a@example.org", STRONG)
    client.force_login(user)
    r = post(client, "/user/update", {"password_current": STRONG, "password_new": "123"})
    assert r.json()["type"] == "weak_password"
    user.refresh_from_db()
    assert user.check_password(STRONG)


# ---------- commands
def test_ensure_dev_admin_creates_an_active_admin(db, monkeypatch):
    monkeypatch.setenv("DEV_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("DEV_ADMIN_PASSWORD", "sportvid-dev-admin")
    call_command("ensure_dev_admin")
    call_command("ensure_dev_admin")  # idempotent
    user = SportVidUser.objects.get(username="admin")
    assert (user.role, user.is_active, user.check_password("sportvid-dev-admin")) == ("admin", True, True)


def test_ensure_dev_admin_refuses_outside_local(db, monkeypatch, settings):
    settings.IS_LOCAL, settings.ENVIRONMENT = False, "prod"
    monkeypatch.setenv("DEV_ADMIN_PASSWORD", "sportvid-dev-admin")
    with pytest.raises(CommandError):
        call_command("ensure_dev_admin")
    assert not SportVidUser.objects.filter(username="admin").exists()


def test_user_add_hides_the_password_and_sets_the_role(db, monkeypatch, capsys):
    answers = iter(["dora", "dora@example.org"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr("backend.management.commands.user_add.getpass", lambda prompt="": STRONG)
    call_command("user_add", role="researcher")
    user = SportVidUser.objects.get(username="dora")
    assert (user.role, user.is_active) == ("researcher", True)
    assert STRONG not in capsys.readouterr().out


def test_user_add_stops_for_existing_names(db, monkeypatch):
    SportVidUser.objects.create_user("dora", "d@example.org", STRONG)
    monkeypatch.setattr("builtins.input", lambda prompt="": "dora")
    monkeypatch.setattr("backend.management.commands.user_add.getpass", lambda prompt="": pytest.fail("asked for a password"))
    call_command("user_add")
    assert SportVidUser.objects.filter(username="dora").count() == 1
