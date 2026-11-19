"""Uploads to the analyser are stored once per content.

Every plugin run uploads its video (and tracking data) to the analyser. The ID of an upload
follows from its content, so a file the analyser already has is neither sent nor stored again.
Client and server talk over a real gRPC channel here; only Ray and Valkey are left out.
"""
import threading
from concurrent import futures
from pathlib import Path

import grpc
import pytest

from analyser.client import AnalyserClient
from analyser.server import AnalyserCacheWrapper, Commune
from data import DataManager
from data.utils import content_data_id
from interface import analyser_pb2, analyser_pb2_grpc


class CountingCommune(Commune):
    """The analyser's servicer with only its data manager, counting the streamed uploads."""

    def __init__(self, data_dir):
        self.managers = {"data_manager": DataManager(str(data_dir))}
        self.uploads = 0

    def upload_file(self, request_iterator, context):
        self.uploads += 1
        return super().upload_file(request_iterator, context)

    def upload_data(self, request_iterator, context):
        self.uploads += 1
        return super().upload_data(request_iterator, context)


@pytest.fixture
def analyser(tmp_path):
    commune = CountingCommune(tmp_path / "analyser")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    analyser_pb2_grpc.add_AnalyserServicer_to_server(commune, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    yield commune, AnalyserClient("127.0.0.1", port, manager=DataManager(str(tmp_path / "client")))
    server.stop(0)


def stored(commune):
    """Every file in the analyser's data folder, partial writes included."""
    root = Path(commune.managers["data_manager"].data_dir)
    return sorted(p.name for p in root.rglob("*") if p.is_file())


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return str(path)


def test_the_same_video_is_stored_once(analyser, tmp_path):
    commune, client = analyser
    video = write(tmp_path / "media" / "a.mp4", b"\x01" * 300_000)

    first = client.upload_file(video)
    second = client.upload_file(video)

    assert first == second
    assert stored(commune) == [f"{first}.zip"]
    assert commune.uploads == 1  # the second run asked and sent nothing


def test_a_copy_under_another_name_is_the_same_data(analyser, tmp_path):
    """The analyser only sees the bytes; a video's file ID or name does not matter."""
    commune, client = analyser
    content = b"\x02" * 1000
    assert client.upload_file(write(tmp_path / "x" / "a.mp4", content)) == \
        client.upload_file(write(tmp_path / "y" / "b.mp4", content))
    assert len(stored(commune)) == 1


def test_different_content_or_type_is_different_data(analyser, tmp_path):
    commune, client = analyser
    ids = {
        client.upload_file(write(tmp_path / "a.mp4", b"\x03" * 1000)),
        client.upload_file(write(tmp_path / "b.mp4", b"\x04" * 1000)),
        client.upload_file(write(tmp_path / "c.csv", b"\x03" * 1000)),  # same bytes, tracking data
    }
    assert len(ids) == 3 and len(stored(commune)) == 3


def test_the_stored_video_is_the_uploaded_one(analyser, tmp_path):
    commune, client = analyser
    content = bytes(range(256)) * 2000
    data_id = client.upload_file(write(tmp_path / "a.mp4", content))

    data = commune.managers["data_manager"].load(data_id)
    with data, data.open_video("r") as f:
        assert data.ext == "mp4" and f.read() == content


def test_concurrent_uploads_of_one_video_leave_one_file(analyser, tmp_path):
    """After a conversion, the thumbnail and camera motion runs upload the video at the same time."""
    commune, client = analyser
    video = write(tmp_path / "a.mp4", b"\x05" * 2_000_000)
    ids, start = [], threading.Barrier(4)

    def run():
        start.wait()
        ids.append(client.upload_file(video))
    threads = [threading.Thread(target=run) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(ids)) == 1 and None not in ids
    assert stored(commune) == [f"{ids[0]}.zip"]  # no partial writes left behind


def test_an_upload_that_does_not_match_its_id_is_discarded(analyser):
    """A transfer that was corrupted (or a client that lies) never takes the content's place."""
    commune, client = analyser
    claimed = content_data_id(analyser_pb2.VIDEO_DATA, "mp4", "0" * 40)
    stub = analyser_pb2_grpc.AnalyserStub(client.channel)

    response = stub.upload_file(iter([analyser_pb2.UploadFileRequest(
        type=analyser_pb2.VIDEO_DATA, data_encoded=b"other bytes", id=claimed, ext="mp4", filename="a.mp4")]))

    assert not response.success
    assert stored(commune) == []
    assert not client.check_data(claimed)


def test_check_data_reports_what_is_stored(analyser, tmp_path):
    commune, client = analyser
    data_id = client.upload_file(write(tmp_path / "a.mp4", b"\x06" * 100))
    assert client.check_data(data_id)
    assert not client.check_data("f" * 32)


def test_results_known_to_the_analyser_are_not_sent_again(analyser):
    """Plugin results the backend passes on as inputs keep their ID."""
    commune, client = analyser
    with client.manager.create_data("StringData") as data:
        data.text = "Tor"

    assert client.upload_data(data) == data.id
    assert client.upload_data(data) == data.id
    assert commune.uploads == 1
    assert stored(commune) == [f"{data.id}.zip"]


class DictCache:
    def __init__(self):
        self.entries = {}

    def get(self, key):
        return self.entries.get(key)

    def set(self, key, value):
        self.entries[key] = value


class FakePlugins:
    def __init__(self, manager):
        self.manager, self.calls = manager, 0

    def plugin_status(self):
        return [{"plugin": "p", "provides": ["text"], "requires": [], "version": "1"}]

    def __call__(self, inputs, data_manager, **kwargs):
        self.calls += 1
        with data_manager.create_data("StringData") as data:
            data.text = "result"
        return {"text": data.id}


def test_a_cached_result_whose_data_is_gone_is_computed_again(tmp_path):
    """With stable input IDs the result cache hits across runs; it must not hand out data that
    no longer exists."""
    manager = DataManager(str(tmp_path))
    plugins = FakePlugins(manager)
    wrapper = AnalyserCacheWrapper(plugins, cache=DictCache())
    call = dict(plugin="p", inputs={}, parameters={}, data_manager=manager, callbacks=[])

    first = wrapper(**call)
    assert wrapper(**call) == first and plugins.calls == 1  # cached

    manager.delete(first["text"])
    again = wrapper(**call)
    assert plugins.calls == 2 and manager.exists(again["text"])
