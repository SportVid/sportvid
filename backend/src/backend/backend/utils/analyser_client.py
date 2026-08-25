import time
import logging
import grpc
from contextlib import nullcontext

from analyser.client import AnalyserClient
from backend.models import PluginRun
from backend.utils import RetryOnRpcErrorClientInterceptor, ExponentialBackoff
from backend.utils.events import cancellation_watcher
from interface import analyser_pb2
from interface import analyser_pb2_grpc


logger = logging.getLogger(__name__)


def map_analyser_progress(progress, progress_range=None):
    """Map the analyser's 0..1 progress into the stage window a task reserved for it.

    Backend tasks set their own coarse milestones around the analyser call (upload,
    post-processing, ...). Without a window both would fight over the same field, so a
    task hands in e.g. (0.1, 0.9) and the analyser's progress fills exactly that slice.
    """
    if progress is None:
        return None
    progress = max(0.0, min(1.0, float(progress)))
    if progress_range is None:
        return progress
    start, end = progress_range
    return start + progress * (end - start)


def analyser_status_to_task_status(analyser_status):
    if analyser_status == analyser_pb2.GetPluginStatusResponse.WAITING:
        return PluginRun.STATUS_WAITING
    if analyser_status == analyser_pb2.GetPluginStatusResponse.RUNNING:
        return PluginRun.STATUS_RUNNING
    if analyser_status == analyser_pb2.GetPluginStatusResponse.ERROR:
        return PluginRun.STATUS_ERROR
    return None


class TaskAnalyserClient(AnalyserClient):
    def __init__(self, *args, plugin_run_db=None, timeout=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin_run_db = plugin_run_db
        self.timeout = timeout
        self.host = kwargs.get("host")
        self.port = kwargs.get("port")

        interceptors = (
            RetryOnRpcErrorClientInterceptor(
                max_attempts=4,
                sleeping_policy=ExponentialBackoff(init_backoff_ms=100, max_backoff_ms=1600, multiplier=2),
                status_for_retry=(grpc.StatusCode.UNAVAILABLE,),
            ),
        )

        self.channel = grpc.intercept_channel(
            grpc.insecure_channel(
                f"{self.host}:{self.port}",
                options=[
                    ("grpc.max_send_message_length", 50 * 1024 * 1024),
                    ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ],
            ),
            *interceptors,
        )

    def list_plugins(self, *args, **kwargs):
        plugin_run_db = self.plugin_run_db
        try:
            return super().list_plugins(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
            if plugin_run_db:
                plugin_run_db.status = PluginRun.STATUS_ERROR
                plugin_run_db.save()
        return None

    def upload_data(self, *args, **kwargs):
        plugin_run_db = self.plugin_run_db
        try:
            return super().upload_data(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
            if plugin_run_db:
                plugin_run_db.status = PluginRun.STATUS_ERROR
                plugin_run_db.save()
        return None

    def upload_file(self, *args, **kwargs):
        plugin_run_db = self.plugin_run_db
        try:
            return super().upload_file(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
            if plugin_run_db:
                plugin_run_db.status = PluginRun.STATUS_ERROR
                plugin_run_db.save()
        return None

    def run_plugin(self, *args, **kwargs):
        plugin_run_db = self.plugin_run_db
        try:
            return super().run_plugin(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
            if plugin_run_db:
                plugin_run_db.status = PluginRun.STATUS_ERROR
                plugin_run_db.save()
        return None

    def abort_plugin(self, *args, **kwargs):
        try:
            return super().abort_plugin(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
        return None

    def get_plugin_status(self, *args, **kwargs):
        plugin_run_db = self.plugin_run_db
        try:
            return super().get_plugin_status(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
            if plugin_run_db:
                plugin_run_db.status = PluginRun.STATUS_ERROR
                plugin_run_db.save()
        return None

    def download_data(self, *args, **kwargs):
        plugin_run_db = self.plugin_run_db
        try:
            return super().download_data(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
            if plugin_run_db:
                plugin_run_db.status = PluginRun.STATUS_ERROR
                plugin_run_db.save()
        return None

    def download_data_to_blob(self, *args, **kwargs):
        plugin_run_db = self.plugin_run_db
        try:
            return super().download_data_to_blob(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
            if plugin_run_db:
                plugin_run_db.status = PluginRun.STATUS_ERROR
                plugin_run_db.save()
        return None

    # 24 hours timeout
    def get_plugin_results(
        self,
        job_id,
        plugin_run_db=None,
        status_fn=None,
        timeout=86400,
        progress_range=None,
    ):
        plugin_run_db = plugin_run_db if plugin_run_db is not None else self.plugin_run_db

        result = None

        start_time = time.time()
        if status_fn is None:
            status_fn = analyser_status_to_task_status

        # Push, not poll: a listener thread reacts the instant the PluginRun is
        # deleted (see views/plugin_run.py's publish_cancel), instead of this loop
        # having to re-check the database itself on every tick. on_cancel fires the
        # analyser abort straight away, from the listener thread, rather than waiting
        # for this loop's next iteration to notice cancel_event and do it.
        watch = (
            nullcontext(None)
            if plugin_run_db is None
            else cancellation_watcher(
                "plugin_run", plugin_run_db.id.hex, on_cancel=lambda: self.abort_plugin(job_id)
            )
        )
        with watch as cancel_event:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    logger.info(f"Plugin run {plugin_run_db.id.hex} cancelled")
                    return None

                if timeout:
                    if time.time() - start_time > timeout:
                        logger.error(f"Timeout")
                        if plugin_run_db:
                            # .update(), not .save(): plugin_run_db may already be gone
                            # by the time this fires (deleted from under a still-running
                            # task) -- .save() on a stale instance would re-insert the
                            # row instead of leaving it deleted (same UUID-pk pitfall as
                            # Video, see tasks/convert_video.py).
                            PluginRun.objects.filter(id=plugin_run_db.id).update(
                                status=PluginRun.STATUS_ERROR
                            )
                        return None
                try:
                    result = self.get_plugin_status(job_id)
                except grpc.RpcError as rpc_error:
                    logger.error(f"GRPC error: code={rpc_error.code()} message={rpc_error.details()}")
                    if plugin_run_db:
                        PluginRun.objects.filter(id=plugin_run_db.id).update(
                            status=PluginRun.STATUS_ERROR
                        )
                    return None
                if result is None:
                    logger.error(f"GRPC error: not a valid return Ccode")
                    if plugin_run_db:
                        PluginRun.objects.filter(id=plugin_run_db.id).update(
                            status=PluginRun.STATUS_ERROR
                        )
                    return None

                if plugin_run_db is not None:
                    update_fields = {}
                    status = status_fn(result.status)
                    if status is not None:
                        update_fields["status"] = status

                    # The analyser has been reporting fine-grained progress all along
                    # (GetPluginStatusResponse.progress, filled from the plugin's
                    # AnalyserProgressCallback) -- it just never made it into the
                    # database, which is why the frontend only ever saw 0 or 1.
                    progress = map_analyser_progress(result.progress, progress_range)
                    if progress is not None and progress > (plugin_run_db.progress or 0.0):
                        update_fields["progress"] = progress
                        plugin_run_db.progress = progress  # keep the `>` comparison above correct across iterations

                    if update_fields:
                        PluginRun.objects.filter(id=plugin_run_db.id).update(**update_fields)

                if result.status == analyser_pb2.GetPluginStatusResponse.UNKNOWN:
                    logger.error("Job is unknown for the analyser")
                    return
                elif result.status == analyser_pb2.GetPluginStatusResponse.WAITING:
                    pass
                elif result.status == analyser_pb2.GetPluginStatusResponse.RUNNING:
                    pass
                elif result.status == analyser_pb2.GetPluginStatusResponse.ERROR:
                    logger.error("Job is crashing")
                    return
                elif result.status == analyser_pb2.GetPluginStatusResponse.DONE:
                    break

                # Event.wait(timeout) returns as soon as cancel_event is set, unlike a
                # plain sleep -- the loop reacts on the next line above almost
                # instantly instead of only after the full second is up.
                if cancel_event is not None:
                    cancel_event.wait(timeout=1.0)
                else:
                    time.sleep(1.0)

        return result
