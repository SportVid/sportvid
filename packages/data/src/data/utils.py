import os
import uuid

# Namespace of the IDs that are derived from a file's content (content_data_id).
CONTENT_ID_NAMESPACE = uuid.UUID("5b1f0e2c-8d4a-4c3e-9a71-2f6d0c8e4b19")


def create_data_path(data_dir, data_id, file_ext):
    os.makedirs(os.path.join(data_dir, data_id[0:2], data_id[2:4]), exist_ok=True)
    data_path = os.path.join(data_dir, data_id[0:2], data_id[2:4], f"{data_id}.{file_ext}")
    return data_path


def generate_id():
    return uuid.uuid4().hex


def content_data_id(data_type, ext, sha1_hex):
    """The data ID of an uploaded file: the same bytes, type and extension always get the same ID,
    so a file that is already stored is not stored again."""
    return uuid.uuid5(CONTENT_ID_NAMESPACE, f"{int(data_type)}:{ext or ''}:{sha1_hex}").hex
