import logging
import sys
import os
import argparse
import time
import uuid
import threading

import yaml
import json
import copy
import traceback
from concurrent import futures
import multiprocessing as mp

from google.protobuf.json_format import MessageToDict


import grpc


from interface import analyser_pb2
from interface import analyser_pb2_grpc
from inference_ray.plugin import AnalyserProgressCallback
from inference_ray.plugin import AnalyserPluginManager
from data import DataManager, Data
from utils.cache import get_hash_for_plugin
from utils.cache import CacheManager
from utils.progress_channel import read_progress, clear_progress


class AnalyserCacheWrapper:
    def __init__(self, plugin: AnalyserPluginManager, cache: CacheManager):
        self.plugin = plugin
        self.cache = cache

    def plugin_status(self):
        return self.plugin.plugin_status()

    def plugins(self):
        return self.plugin._plugins

    def __call__(self, plugin, inputs, parameters, data_manager, callbacks, cancel_event=None, session=None, job_id=None):
        cached = False
        if self.cache:
            plugins = {x["plugin"]: x for x in self.plugin.plugin_status()}

            run_id = uuid.uuid4().hex[:4]
            if plugin not in plugins:
                logging.error(
                    f"[AnalyserCacheWrapper] {run_id} plugin: {plugin} not found"
                )
                return None

            plugin_to_run = plugins[plugin]
            results = {}
            logging.info(f"[AnalyserPluginManager] {run_id} Cache {plugin_to_run}")
            logging.info(
                f"[AnalyserPluginManager] {run_id} Cache {plugin_to_run['provides']}"
            )
            logging.info(
                f"[AnalyserPluginManager] {run_id} Cache {plugin_to_run['requires']}"
            )

            print(inputs, flush=True)
            cached = True
            for output in plugin_to_run["provides"]:
                result_hash = get_hash_for_plugin(
                    plugin=plugin,
                    output=output,
                    inputs=[x.id for _, x in inputs.items()],
                    parameters=parameters,
                    version=plugin_to_run["version"],
                    config={},  # plugin_to_run.config, TODO
                )

                logging.info(f"[AnalyserPluginManager] {run_id} Cache {result_hash}")
                cached_data = self.cache.get(result_hash)
                if cached_data is None:
                    cached = False
                    break

                logging.info(
                    f"[AnalyserPluginManager] {run_id} Cache get {result_hash} {cached_data}"
                )
                results[output] = cached_data.get("data_id")

        if not cached:
            logging.info(f"[AnalyserPluginManager] {run_id} plugin: {plugin_to_run}")
            logging.info(
                f"[AnalyserPluginManager] {run_id} data: {[{k:x.id} for k,x in inputs.items()]}"
            )
            logging.info(f"[AnalyserPluginManager] {run_id} parameters: {parameters}")
            results = self.plugin(
                plugin=plugin,
                inputs=inputs,
                data_manager=data_manager,
                parameters=parameters,
                callbacks=callbacks,
                cancel_event=cancel_event,
                session=session,
                job_id=job_id,
            )
            logging.info(
                f"[AnalyserPluginManager] {run_id} results: {[{k:x} for k,x in results.items()]}"
            )

        if self.cache:
            for output, data in results.items():
                data_id = data
                logging.debug(f"#####DEBUG {data_id} {data} {isinstance(data, Data)}")

                result_hash = get_hash_for_plugin(
                    plugin=plugin,
                    output=output,
                    inputs=[x.id for _, x in inputs.items()],
                    parameters=parameters,
                    version=plugin_to_run["version"],
                    config={},  # plugin_to_run.config, TODO
                )
                logging.info(
                    f"[AnalyserPluginManager] Cache set {result_hash} {data_id}"
                )

                self.cache.set(
                    result_hash,
                    {"data_id": data_id, "time": time.time(), "type": "plugin_result"},
                )
        return results

# TODO: Add explicit timeouts to plugin HTTP calls and ensure session.close()
# actually interrupts in-flight requests quickly enough.
# TODO: Implement periodic cleanup of cancel_events and sessions dicts to
# prevent unbounded growth in long-running analyser processes.
def run_plugin(args):
    try:
        plugin_manager = globals().get("plugin_manager")
        data_manager = globals().get("data_manager")
        params = args.get("params")
        shared = args.get("shared")
        cancel_event = args.get("cancel_event")
        session_holder = args.get("session_holder")
        shared["progress"] = 0.0
        shared["status"] = analyser_pb2.GetPluginStatusResponse.RUNNING

        if cancel_event is not None and cancel_event.is_set():
            logging.info(f"[Analyser] {params.get('plugin')} aborted before it started")
            return []

        plugin_inputs = {}
        if "inputs" in params:
            for data_in in params.get("inputs"):
                data = data_manager.load(data_in.get("id"))
                if data is None:
                    logging.error(f"Data not found {data_in.get('id')}")
                    return []
                plugin_inputs[data_in.get("name")] = data

        plugin_parameters = {}
        if "parameters" in params:
            for parameter in params.get("parameters"):
                if parameter.get("type") == "BOOL_TYPE":
                    plugin_parameters[parameter.get("name")] = json.loads(
                        parameter.get("value")
                    )
                if parameter.get("type") == "INT_TYPE":
                    plugin_parameters[parameter.get("name")] = int(
                        parameter.get("value")
                    )                
                if parameter.get("type") == "FLOAT_TYPE":
                    plugin_parameters[parameter.get("name")] = float(
                        parameter.get("value")
                    )
                if parameter.get("type") == "STRING_TYPE":
                    plugin_parameters[parameter.get("name")] = str(
                        parameter.get("value")
                    )
                if parameter.get("type") == "DICT_TYPE":
                    plugin_parameters[parameter.get("name")] = json.loads(
                        parameter.get("value")
                    )
        
        callbacks = [AnalyserProgressCallback(shared)]

        # Before invoking the plugin_manager the worker creates a dedicated HTTP session.
        # Cancellation ahndler can later close this exact session from another thread.
        # Closing it is intended to interrupt the HTTP request from the analyser service to Ray Serve.
        import requests
        session = requests.Session()
        if session_holder is not None:
            session_holder["session"] = session

        results = plugin_manager(
            plugin=params.get("plugin"),
            inputs=plugin_inputs,
            parameters=plugin_parameters,
            data_manager=data_manager,
            callbacks=callbacks,
            cancel_event=cancel_event,
            session=session,
            job_id=args.get("id"),
        )
        if results is None:
            logging.error(f"[Analyser] {params.get('plugin')} without results")
            return []

        result_map = []
        for key, id in results.items():
            # data_manager.save(data)
            result_map.append({"name": key, "id": id})

        return result_map
    except Exception as e:
        # raise e
        logging.error(f"[Analyser] {repr(e)}")
        exc_type, exc_value, exc_traceback = sys.exc_info()

        traceback.print_exception(
            exc_type,
            exc_value,
            exc_traceback,
            limit=2,
            file=sys.stdout,
        )


def init_plugins(config):
    data_dict = {}

    # building datamanager
    data_config = config.get("data", None)
    data_dir = None
    cache = None

    if data_config is not None:
        data_dir = data_config.get("data_dir", None)
        cache_config = data_config.get("cache")
        if cache_config is not None:
            cache = CacheManager.build(
                name=cache_config["type"], config=cache_config["params"]
            )

    data_manager = DataManager(data_dir=data_dir, cache=cache)
    data_dict["data_manager"] = data_manager

    ray_config = config.get("inference", {})
    if "type" not in ray_config:
        ray_config["type"] = "ray"

    if "params" not in ray_config:
        ray_config["params"] = {"host": "inference_ray", "port": 52365}

    manager = AnalyserCacheWrapper(
        AnalyserPluginManager(ray_config["params"]), cache=cache
    )
    data_dict["plugin_manager"] = manager

    return data_dict


def init_process(config):
    globals().update(init_plugins(config))


class Commune(analyser_pb2_grpc.AnalyserServicer):
    def __init__(self, config):
        self.config = config
        self.managers = init_plugins(config)
        self.process_pool = futures.ThreadPoolExecutor(
            max_workers=self.config.get("num_worker", 4),
            initializer=init_process,
            initargs=(config,),
        )
        self.shared_manager = mp.Manager()
        self.futures = []

        # Cancellation bookkeeping, deliberately uses ordinary dicts rather than mp.Manager objects.
        # This is because the jobs run through a ThreadPoolExecutor, not a process pool.
        self._cancel_lock = threading.Lock()
        self.cancel_events = {}
        self.sessions = {}

    def list_plugins(self, request, context):
        reply = analyser_pb2.ListPluginsReply()

        # print(self.managers["plugin_manager"].plugin_status())
        for _, plugin_class in self.managers["plugin_manager"].plugins().items():
            reply.plugins.extend([analyser_pb2.PluginInfo(name=plugin_class._name)])

        return reply

    def upload_data(self, request_iterator, context):
        try:
            data, hash = self.managers["data_manager"].load_data_from_stream(
                request_iterator
            )
            data_id = None
            with data:
                data_id = data.id
            return analyser_pb2.UploadDataResponse(success=True, id=data_id, hash=hash)

        except Exception as e:
            logging.error(f"[Analyser] {repr(e)}")
            logging.error(traceback.format_exc())
            context.set_code(grpc.StatusCode.DATA_LOSS)
            context.set_details(f"Error transferring data with id {data.id}")
            return analyser_pb2.UploadDataResponse(success=False)

    def upload_file(self, request_iterator, context):
        # try:
        data, hash = self.managers["data_manager"].load_file_from_stream(
            request_iterator
        )
        # data, hash = self.managers["data_manager"].load_data_from_stream(
        #   request_iterator
        # )

        return analyser_pb2.UploadDataResponse(success=True, id=data.id, hash=hash)

        # except Exception as e:
        #     logging.error(f"[Analyser] {repr(e)}")
        #     logging.error(traceback.format_exc())
        #     context.set_code(grpc.StatusCode.DATA_LOSS)
        #     context.set_details(f"Error transferring data with id {data.id}")
        #     return analyser_pb2.UploadDataResponse(success=False)

    def check_data(self, request, context):
        try:
            data = self.managers["data_manager"].check(request.id)
            if data is not None:
                return analyser_pb2.CheckDataResponse(exists=True)
            return analyser_pb2.CheckDataResponse(exists=False)

        except Exception as e:
            logging.error(f"[Analyser] {repr(e)}")
            logging.error(traceback.format_exc())
            return analyser_pb2.CheckDataResponse(exists=False)

    def run_plugin(self, request, context):
        # if request.plugin not in self.managers["plugin_manager"].plugins():
        #     return analyser_pb2.RunPluginResponse(success=False)

        job_id = uuid.uuid4().hex
        variable = {
            "params": MessageToDict(request),
            "config": self.config,
            "future": None,
            "id": job_id,
        }
        process_args = copy.deepcopy(variable)

        d = self.shared_manager.dict()
        d["progress"] = 0.0
        d["status"] = analyser_pb2.GetPluginStatusResponse.WAITING
        variable["shared"] = d
        process_args["shared"] = d

        # Objects must remain shared references and must not be copied with deepcopy.
        # Event/dict has to stay the *same* object in both self.cancel_events/self.sessions (for abort_plugin to reach) 
        # & process_args (for the worker thread to see), which deepcopy would break.
        cancel_event = threading.Event()
        session_holder = {}
        with self._cancel_lock:
            self.cancel_events[job_id] = cancel_event
            self.sessions[job_id] = session_holder
        process_args["cancel_event"] = cancel_event
        process_args["session_holder"] = session_holder

        future = self.process_pool.submit(run_plugin, process_args)
        variable["future"] = future
        self.futures.append(variable)

        return analyser_pb2.RunPluginResponse(success=True, id=job_id)

    def abort_plugin(self, request, context):
        job_id = request.id
        # find the job
        futures_lut = {x["id"]: i for i, x in enumerate(self.futures)}
        if job_id not in futures_lut:
            logging.warning(f"[Analyser] abort_plugin: unknown job {job_id}")
            return analyser_pb2.AbortPluginResponse(success=False)

        job_data = self.futures[futures_lut[job_id]]
        # retrieve the cancellation status
        with self._cancel_lock:
            cancel_event = self.cancel_events.get(job_id)
            session_holder = self.sessions.get(job_id)
        if cancel_event is not None:
            cancel_event.set() # set cancellation event -> inform worker and plugin that cancellation was requested

        # cancel jobs that have not started -> if the future is still queued, shared status is set to ERROR, method returns
        if job_data["future"].cancel():
            job_data["shared"]["status"] = analyser_pb2.GetPluginStatusResponse.ERROR
            logging.info(f"[Analyser] job {job_id} cancelled before it started")
            return analyser_pb2.AbortPluginResponse(success=True)

        # 1. Close the analyser-to-Ray HTTP session:
        #   - retrieve the dedicated HTTP session for a running job
        #   - forces blocked HTTP call to the ray serve deployment to unblock
        # 2. Cause the Ray Serve request to be cancelled.
        #   - worker thread notices cancel_event and returns
        #   - closing the connection from here is also what makes Ray Serve's own request cancellation kick in on the
        #   - deployment side (see inference_ray/main.py's run_in_executor + CancelledError).
        # 3. Make the analyser-side plugin request return.
        # 4. Let cancel_event terminate the backend polling loop.
        session = (session_holder or {}).get("session")
        if session is not None:
            try:
                session.close()
            except Exception:
                logging.exception(f"[Analyser] failed to close session for job {job_id}")

        logging.info(f"[Analyser] abort requested for running job {job_id}")
        return analyser_pb2.AbortPluginResponse(success=True)

    def get_plugin_status(self, request, context):
        futures_lut = {x["id"]: i for i, x in enumerate(self.futures)}
        response = analyser_pb2.GetPluginStatusResponse()
        if request.id in futures_lut:
            job_data = self.futures[futures_lut[request.id]]
            done = job_data["future"].done()

            status = job_data["shared"].get(
                "status", analyser_pb2.GetPluginStatusResponse.UNKNOWN
            )
            response.status = status

            progress = job_data["shared"].get("progress", 0.0) # read via valkey (see, utils.progress_channel.py)
            
            bridged = read_progress(request.id)
            if bridged is not None:
                progress = max(progress, bridged)
            response.progress = progress
            if not done:
                return response
            clear_progress(request.id)

            try:
                results = job_data["future"].result()

                if results is None:
                    response.status = analyser_pb2.GetPluginStatusResponse.ERROR
                    return response
                for k in results:
                    output = response.outputs.add()
                    output.name = k["name"]
                    output.id = k["id"]

            except Exception as e:
                logging.error(f"[Analyser] {repr(e)}")
                logging.error(traceback.format_exc())
                logging.error(traceback.print_stack())

                response.status = analyser_pb2.GetPluginStatusResponse.ERROR
                return response

            response.status = analyser_pb2.GetPluginStatusResponse.DONE
            return response
        response.status = analyser_pb2.GetPluginStatusResponse.UNKNOWN

        return response

    def download_data(self, request, context):
        try:
            for x in self.managers["data_manager"].dump_to_stream(request.id):
                yield analyser_pb2.DownloadDataResponse(
                    id=x["id"], data_encoded=x["data_encoded"]
                )

        except Exception as e:
            logging.error(f"[Analyser] {repr(e)}")
            logging.error(traceback.format_exc())
            context.set_code(grpc.StatusCode.DATA_LOSS)
            context.set_details(f"Error transferring data with id {request.id}")
            return analyser_pb2.DownloadDataResponse()


class Server:
    def __init__(self, config):
        self.config = config

        self.commune = Commune(config)

        pool = futures.ThreadPoolExecutor(max_workers=10)

        self.server = grpc.server(
            pool,
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ],
        )
        analyser_pb2_grpc.add_AnalyserServicer_to_server(
            self.commune,
            self.server,
        )

        grpc_config = config.get("grpc", {})
        port = grpc_config.get("port", 50051)
        self.server.add_insecure_port(f"[::]:{port}")

    def run(self):
        logging.info("[Server] starting")
        self.server.start()
        logging.info("[Server] ready")

        try:
            while True:
                num_jobs = len(self.commune.futures)
                num_jobs_done = len(
                    [x for x in self.commune.futures if x["future"].done()]
                )
                self.server
                time.sleep(10)
        except KeyboardInterrupt:
            self.server.stop(0)


def read_config(path):
    with open(path, "r") as f:
        raw_cfg_str = f.read()
        expanded_cfg_str = os.path.expandvars(raw_cfg_str)
        return yaml.safe_load(expanded_cfg_str)


def parse_args():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-d", "--debug", action="store_true", help="debug output")
    parser.add_argument("-c", "--config", help="config path")
    parser.add_argument("--port", type=int, help="port")
    parser.add_argument("--host", help="host")
    parser.add_argument("--data_dir", help="data dir")
    parser.add_argument("--no_cache", action="store_true", help="disable cache")
    parser.add_argument("--cache_valkey_host", help="valkey cache host")
    parser.add_argument("--cache_valkey_port", type=int, help="valkey cache port")
    parser.add_argument("--inference_ray_host", help="inference ray host")
    parser.add_argument("--inference_ray_port", type=int, help="inference ray port")
    parser.add_argument(
        "--inference_ray_status_port", type=int, help="inference ray port"
    )

    args = parser.parse_args()

    return args


def main():
    args = parse_args()

    level = logging.ERROR
    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO

    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
        level=level,
    )

    if args.config is not None:
        config = read_config(args.config)
    else:
        config = {}

    if args.port:
        if "grpc" not in config:
            config["grpc"] = {}
        config["grpc"]["port"] = args.port

    if args.host:
        if "grpc" not in config:
            config["grpc"] = {}
        config["grpc"]["host"] = args.host

    if args.data_dir:
        if "data" not in config:
            config["data"] = {}
        config["data"]["data_dir"] = args.data_dir

    if args.no_cache:
        if "data" not in config:
            config["data"] = {}
        config["data"]["cache"] = None

    if args.cache_valkey_host:
        if "data" not in config:
            config["data"] = {}
        if "cache" not in config["data"]:
            config["data"]["cache"] = {"type": "valkey", "params": {}}
        config["data"]["cache"]["params"]["host"] = args.cache_valkey_host

    if args.cache_valkey_port:
        if "data" not in config:
            config["data"] = {}
        if "cache" not in config["data"]:
            config["data"]["cache"] = {"type": "valkey", "params": {}}
        config["data"]["cache"]["params"]["port"] = args.cache_valkey_port

    if args.inference_ray_host:
        if "inference" not in config:
            config["inference"] = {
                "type": "ray",
                "params": {
                    "host": "inference_ray", 
                    "status_port": 52365, 
                    "port": 8010,
                },
            }
        if "params" not in config["inference"]:
            config["inference"]["params"] = {
                "host": "inference_ray",
                "status_port": 52365,
                "port": 8010,
            }
        config["inference"]["params"]["host"] = args.inference_ray_host

    if args.inference_ray_status_port:
        if "inference" not in config:
            config["inference"] = {
                "type": "ray",
                "params": {
                    "host": "inference_ray", 
                    "status_port": 52365, 
                    "port": 8010,
                },
            }
        if "params" not in config["inference"]:
            config["inference"]["params"] = {
                "host": "inference_ray",
                "status_port": 52365,
                "port": 8010,
            }
        config["inference"]["params"]["status_port"] = args.inference_ray_status_port

    if args.inference_ray_port:
        if "inference" not in config:
            config["inference"] = {
                "type": "ray",
                "params": {
                    "host": "inference_ray", 
                    "status_port": 52365, 
                    "port": 8010,
                },
            }
        if "params" not in config["inference"]:
            config["inference"]["params"] = {
                "host": "inference_ray",
                "status_port": 52365,
                "port": 8010,
            }
        config["inference"]["params"]["port"] = args.inference_ray_port

    server = Server(config)
    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
