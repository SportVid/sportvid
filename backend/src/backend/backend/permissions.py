"""Object-level access rules.

Who may access an object:

    role        own objects     other users' objects
    user        read + write    -
    researcher  read + write    read
    admin       read + write    read + write

Views resolve every ID taken from a request through `readable()` or `writable()`, so an
object the user may not access behaves exactly like one that does not exist.
"""
from django.db.models import Model, QuerySet

READ_ALL_ROLES = frozenset({"admin", "researcher"})
WRITE_ALL_ROLES = frozenset({"admin"})

# Lookup path from each model to the user that owns it.
OWNER_PATHS = {
    "Video": "owner",
    "TrackingData": "owner",
    "PluginRun": "video__owner",
    "PluginRunResult": "plugin_run__video__owner",
    "Timeline": "video__owner",
    "TimelineSegment": "timeline__video__owner",
    "TimelineSegmentAnnotation": "timeline_segment__timeline__video__owner",
    "Annotation": "owner",
    "AnnotationCategory": "owner",
    "Shortcut": "owner",
    "AnnotationShortcut": "shortcut__owner",
    "ClusterTimelineItem": "plugin_run__video__owner",
    "ClusterItem": "plugin_run_result__plugin_run__video__owner",
    "VideoAnalysisState": "video__owner",
    "CalibrationAssets": "owner",
}


def _role(user):
    return getattr(user, "role", None) if user is not None and user.is_authenticated else None


def can_read_all(user) -> bool:
    return _role(user) in READ_ALL_ROLES


def can_write_all(user) -> bool:
    return _role(user) in WRITE_ALL_ROLES


def _scoped(model_or_queryset, user, write: bool) -> QuerySet:
    if isinstance(model_or_queryset, QuerySet):
        queryset = model_or_queryset
    elif isinstance(model_or_queryset, type) and issubclass(model_or_queryset, Model):
        queryset = model_or_queryset._default_manager.all()
    else:
        raise TypeError(f"expected a model class or queryset, got {model_or_queryset!r}")

    if user is None or not user.is_authenticated:
        return queryset.none()
    if (can_write_all if write else can_read_all)(user):
        return queryset
    return queryset.filter(**{OWNER_PATHS[queryset.model.__name__]: user})


def readable(model_or_queryset, user) -> QuerySet:
    """Objects `user` may read: their own, or all of them for admins and researchers."""
    return _scoped(model_or_queryset, user, write=False)


def writable(model_or_queryset, user) -> QuerySet:
    """Objects `user` may modify: their own, or all of them for admins."""
    return _scoped(model_or_queryset, user, write=True)


# Plugin parameters that refer to other objects by ID (see backend/tasks/*.py). A plugin
# run may only use objects its user can read.
PARAMETER_REFERENCES = {
    "tracking_data_id": "TrackingData",
    "calibration_id": "CalibrationAssets",
    "object_tracker_id": "PluginRun",
    "object_tracker_run_id": "PluginRun",
    "osnet_reid_id": "PluginRun",
    "scalar_timeline_id": "Timeline",
    "shot_timeline_id": "Timeline",
    "timeline_ids": "Timeline",
    "cluster_timeline_item_id": "ClusterTimelineItem",
}


def unreadable_references(parameters, user) -> list:
    """Names of the parameters in `parameters` that refer to objects `user` cannot read."""
    import uuid

    from django.apps import apps

    denied = []
    for name, model_name in PARAMETER_REFERENCES.items():
        value = (parameters or {}).get(name)
        if value in (None, "", []):
            continue
        try:
            ids = {uuid.UUID(str(v)) for v in (value if isinstance(value, (list, tuple)) else [value])}
        except ValueError:
            denied.append(name)
            continue
        model = apps.get_model("backend", model_name)
        if readable(model, user).filter(id__in=ids).count() != len(ids):
            denied.append(name)
    return denied
