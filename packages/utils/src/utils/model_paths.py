"""Guard for model weight files (docs/adr/0004).

Loading weights unpickles them, so a plugin must only load files from the server's model
folder, never a path or URL that arrived with a request.
"""
import os

MODELS_ROOT = "/models"


def checked_model_path(path, root: str = MODELS_ROOT) -> str:
    """Return `path` unchanged if it is an absolute path inside `root`, else raise ValueError.

    The check is lexical (normpath), so symlinks inside `root` keep working while `..`
    segments, relative paths and URLs are rejected.
    """
    value = str(path)
    normalized = os.path.normpath(value)
    if not os.path.isabs(value) or not normalized.startswith(root.rstrip("/") + "/"):
        raise ValueError(f"model file must be a path under {root}: {value!r}")
    return value
