import time
import logging
import grpc
from django.conf import settings
from contextlib import nullcontext

from django.utils import timezone

from analyser.client import AnalyserClient
from backend.models import PluginRun
from backend.utils import RetryOnRpcErrorClientInterceptor, ExponentialBackoff
from backend.utils.eta import EtaEstimator
from backend.log_context import log_context, log_event
from backend.utils.events import cancellation_watcher, publish_plugin_run
from interface import analyser_pb2
from interface import analyser_pb2_grpc


logger = logging.getLogger(__name__)


def map_analyser_progress(progress, progress_range=None):
    """ Helper function to map the analyser progress. """
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


def _fail_run(plugin_run, **fields):
    """Mark the run ERROR, unless it was deleted meanwhile: save() would insert it again.

    .update() skips post_save, so the live event is sent here.
    """
    if plugin_run is None:
        return
    fields = {"status": PluginRun.STATUS_ERROR, "eta_seconds": None, **fields}
    updated = PluginRun.objects.filter(id=plugin_run.id).update(update_date=timezone.now(), **fields)
    for name, value in fields.items():
        setattr(plugin_run, name, value)
    if not updated:
        log_event(logger, "plugin_run.deleted_while_running", plugin_run_id=plugin_run.id, status="error")
        return
    try:
        publish_plugin_run(plugin_run)
    except Exception:
        logger.warning("Failed to publish plugin run ERROR event", exc_info=True)


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

    def _grpc_failed(self, call, rpc_error, plugin_run=None):
        code = rpc_error.code()
        log_event(logger, "analyser.grpc_error", level=logging.ERROR,
                  call=call, code=getattr(code, "name", code), message=rpc_error.details())
        _fail_run(plugin_run)

    def list_plugins(self, *args, **kwargs):
        try:
            return super().list_plugins(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            self._grpc_failed("list_plugins", rpc_error, self.plugin_run_db)
        return None

    def upload_data(self, *args, **kwargs):
        try:
            return super().upload_data(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            self._grpc_failed("upload_data", rpc_error, self.plugin_run_db)
        return None

    def upload_file(self, *args, **kwargs):
        try:
            return super().upload_file(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            self._grpc_failed("upload_file", rpc_error, self.plugin_run_db)
        return None

    def run_plugin(self, *args, **kwargs):
        try:
            return super().run_plugin(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            self._grpc_failed("run_plugin", rpc_error, self.plugin_run_db)
        return None

    def abort_plugin(self, *args, **kwargs):
        try:
            return super().abort_plugin(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            self._grpc_failed("abort_plugin", rpc_error)
        return None

    def get_plugin_status(self, *args, **kwargs):
        try:
            return super().get_plugin_status(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            self._grpc_failed("get_plugin_status", rpc_error, self.plugin_run_db)
        return None

    def download_data(self, *args, **kwargs):
        try:
            return super().download_data(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            self._grpc_failed("download_data", rpc_error, self.plugin_run_db)
        return None

    def download_data_to_blob(self, *args, **kwargs):
        try:
            return super().download_data_to_blob(*args, **kwargs)
        except grpc.RpcError as rpc_error:
            self._grpc_failed("download_data_to_blob", rpc_error, self.plugin_run_db)
        return None

    def get_plugin_results(
        self,
        job_id,
        plugin_run_db=None,
        status_fn=None,
        timeout=None,  # default: settings.PLUGIN_RUN_TIMEOUT
        progress_range=None,
    ):
        plugin_run_db = plugin_run_db if plugin_run_db is not None else self.plugin_run_db
        if timeout is None:
            timeout = settings.PLUGIN_RUN_TIMEOUT

        result = None

        start_time = time.time()
        eta_estimator = EtaEstimator()
        if status_fn is None:
            status_fn = analyser_status_to_task_status

        # Wraps the analyser polling into a cancellation watcher that is active for DB-backed plugin runs.
        # This listener thread reacts immediately when a PluginRun is deleted (see, views/plugin_run.py's publish_cancel()).
        watch = (
            nullcontext(None)
            if plugin_run_db is None
            else cancellation_watcher(
                "plugin_run", plugin_run_db.id.hex, on_cancel=lambda: self.abort_plugin(job_id)
            )
        )
        with log_context(job_id=job_id), watch as cancel_event:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    log_event(logger, "plugin_run.cancelled", plugin_run_id=plugin_run_db.id, source="valkey")
                    return None

                if timeout:
                    if time.time() - start_time > timeout:
                        logger.error("Analyser job %s exceeded %s s, aborting it", job_id, timeout)
                        try:
                            self.abort_plugin(job_id)  # free the analyser worker and the Ray call
                        except Exception:
                            logger.warning("Could not abort analyser job %s", job_id, exc_info=True)
                        _fail_run(plugin_run_db, failure_reason={
                            "type": "analyser_timeout",
                            "message": f"The analysis did not finish within {timeout:g} s",
                            "details": {"timeout_seconds": timeout},
                        })
                        return None
                result = self.get_plugin_status(job_id)
                if result is None:
                    # gRPC error: get_plugin_status() logged it and marked self.plugin_run_db failed
                    if plugin_run_db is not self.plugin_run_db:
                        _fail_run(plugin_run_db)
                    return None

                if plugin_run_db is not None:
                    # add status when available & progress when it advances
                    update_fields = {}
                    status = status_fn(result.status)
                    if status is not None:
                        update_fields["status"] = status

                    # TODO: prevents regressions if a task uses multiple analyser calls with different progress_range, later phases may be suppressed
                    # --> if tasks start using multiple analyser phases, add a phase/sequence field to PluginRun and enforce monotonic progress per phase instead of globally. 
                    # maps analyser progress into the task's progress and persist it into the DB
                    progress = map_analyser_progress(result.progress, progress_range)
                    if progress is not None and progress > (plugin_run_db.progress or 0.0):
                        update_fields["progress"] = progress
                        update_fields["eta_seconds"] = eta_estimator.update(progress)
                        plugin_run_db.progress = progress

                    if update_fields:
                        # auto_now doesn't fire on a queryset .update(), so bump it here
                        # -- the frontend uses update_date as a change signal.
                        update_fields.setdefault("update_date", timezone.now())
                        if not PluginRun.objects.filter(id=plugin_run_db.id).update(**update_fields):
                            # the run was deleted and its cancel message never arrived (Valkey down,
                            # or sent before the watcher subscribed): stop the analyser job anyway
                            log_event(logger, "plugin_run.cancelled", plugin_run_id=plugin_run_db.id,
                                      source="db_fallback")
                            self.abort_plugin(job_id)
                            return None
                        # .update() skips post_save, so push the live event ourselves --
                        # otherwise the status list only ever sees QUEUED then DONE.
                        for field, value in update_fields.items():
                            setattr(plugin_run_db, field, value)
                        try:
                            publish_plugin_run(plugin_run_db)
                        except Exception:
                            logger.warning(
                                "Failed to publish plugin run progress event", exc_info=True
                            )

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
                # plain sleep. The loop reacts on the next line above almost
                # instantly instead of only after the full second is up.
                if cancel_event is not None:
                    cancel_event.wait(timeout=1.0)
                else:
                    time.sleep(1.0)

        return result
