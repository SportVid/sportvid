"""Every typed data object survives save -> load, and the gRPC stream between analyser and backend.

These are the contract between the Ray plugins, the analyser and the backend (packages/data).
A new data type (T18) gets a sample in SAMPLES; the guard test below fails until it has one,
or until it is listed in NOT_YET_SAMPLED on purpose.
"""
import tempfile

import numpy as np
import pytest

from data import DataManager
from data.plugins.shot_data import Shot
from data.plugins.string_data import StringData
from interface import analyser_pb2

SAMPLES = {
    "ScalarData": dict(y=np.array([0.1, 0.5, 0.9]), time=np.array([0.0, 0.04, 0.08]), delta_time=0.04),
    "HistData": dict(hist=np.arange(6.0).reshape(2, 3), time=np.array([0.0, 1.0]), delta_time=1.0),
    "RGBData": dict(colors=np.arange(6.0).reshape(2, 3), time=np.array([0.0, 1.0]), delta_time=1.0),
    "BboxesData": dict(bboxes='{"0": [[1, 3, 0.1, 0.1, 0.2, 0.2]]}', meta_data='{"fps": 25}'),
    "KpiData": dict(tracking_data_id="t1", meta_data='{"fps": 25}', kpis='{"distance": [1.0, 2.0]}'),
    "PositionData": dict(tracking_data_id="t1", meta_data='{"fps": 25}', pos='{"1": [[0.0, 1.0]]}'),
    "TeamsData": dict(teams_data_id="t1", teams_data='{"1": 0, "2": 1}'),
    "StringData": dict(text="Tor für Fulda"),
    "StringsData": dict(strings=[StringData(text="a"), StringData(text="b")]),
    "ShotsData": dict(shots=[Shot(start=0.0, end=2.5), Shot(start=2.5, end=4.0)]),
}

# Registered types without a sample yet. Shrink this list; don't grow it.
# ListData is covered by its own test below.
NOT_YET_SAMPLED = {
    "AnnotationData", "AudioData", "ClusterData", "DictData", "FacesData", "FloodlightData",
    "ImageEmbeddings", "ImagesData", "KpssData", "ListData", "ReIDData", "TextEmbeddings",
    "TrackingData", "VideoAssetData", "VideoData", "VideoTemporalEmbeddings",
}


@pytest.fixture
def manager():
    return DataManager(tempfile.mkdtemp())


def _store(manager, data_type, fields):
    with manager.create_data(data_type) as data:
        for name, value in fields.items():
            setattr(data, name, value)
    return data.id


def _as_dict(manager, data_id):
    data = manager.load(data_id)
    with data:
        return data.to_dict()


def _expected(data_type, fields, data_id):
    with DataManager(tempfile.mkdtemp()).create_data(data_type, data_id) as data:
        for name, value in fields.items():
            setattr(data, name, value)
        return data.to_dict()


def test_every_registered_type_is_sampled_or_listed():
    registered = set(DataManager._data_name_lut)
    assert registered - set(SAMPLES) - NOT_YET_SAMPLED == set(), "add a sample for the new data type"
    assert NOT_YET_SAMPLED - registered == set(), "remove types that no longer exist"
    assert set(SAMPLES) & NOT_YET_SAMPLED == set(), "sampled types don't belong in NOT_YET_SAMPLED"


@pytest.mark.parametrize("data_type", sorted(SAMPLES))
def test_save_and_load(manager, data_type):
    data_id = _store(manager, data_type, SAMPLES[data_type])
    assert _as_dict(manager, data_id) == _expected(data_type, SAMPLES[data_type], data_id)


@pytest.mark.parametrize("data_type", sorted(SAMPLES))
def test_transfer_through_the_grpc_stream(manager, data_type):
    """analyser -> backend: download_data wraps dump_to_stream chunks in DownloadDataResponse."""
    data_id = _store(manager, data_type, SAMPLES[data_type])
    receiver = DataManager(tempfile.mkdtemp())

    chunks = (
        analyser_pb2.DownloadDataResponse(id=x["id"], data_encoded=x["data_encoded"])
        for x in manager.dump_to_stream(data_id, chunk_size=64)  # small chunks: force several messages
    )
    received, _ = receiver.load_data_from_stream(chunks)

    assert received.id == data_id
    assert _as_dict(receiver, data_id) == _as_dict(manager, data_id)


def test_list_of_nested_data_survives_the_stream(manager):
    with manager.create_data("ListData") as frames:
        for t in (0.0, 1.0):
            with frames.create_data("ScalarData") as scalar:
                scalar.y, scalar.time, scalar.delta_time = np.array([t]), np.array([t]), 1.0
    receiver = DataManager(tempfile.mkdtemp())

    chunks = (analyser_pb2.DownloadDataResponse(id=x["id"], data_encoded=x["data_encoded"])
              for x in manager.dump_to_stream(frames.id))
    receiver.load_data_from_stream(chunks)

    received = _as_dict(receiver, frames.id)
    assert received == _as_dict(manager, frames.id)
    assert received["index"] == [0, 1]
    assert [d["y"] for d in received["data"]] == [[0.0], [1.0]]


def test_delete(manager):
    data_id = _store(manager, "StringData", SAMPLES["StringData"])
    manager.delete(data_id)
    assert manager.load(data_id) is None
