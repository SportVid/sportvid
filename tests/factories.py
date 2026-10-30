"""Small builders for the rows most tests need. Keyword arguments override any field."""
from backend.models import PluginRun, SportVidUser, Video

PASSWORD = "Correct-Horse-Battery-42"


def make_user(username="alice", role="user", **fields):
    user = SportVidUser.objects.create_user(username, f"{username}@example.org", PASSWORD)
    user.role = role
    for name, value in fields.items():
        setattr(user, name, value)
    user.save()
    return user


def make_video(owner, **fields):
    fields = {"name": "video", "ext": ".mp4", "duration": 10.0, "fps": 25.0, "width": 1920, "height": 1080, **fields}
    return Video.objects.create(owner=owner, **fields)


def make_run(video, type="object_tracker", status=PluginRun.STATUS_QUEUED, **fields):
    return PluginRun.objects.create(video=video, type=type, status=status, **fields)
