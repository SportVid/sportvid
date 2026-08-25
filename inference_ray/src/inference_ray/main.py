import asyncio
import functools
import logging
from ray import serve
from typing import Dict
from ray.serve import Application

from data import DataManager
from inference_ray.plugin import AnalyserPluginManager, AnalyserPlugin


@serve.deployment
class Deployment:
    def __init__(self, plugin: AnalyserPlugin, data_manager: DataManager) -> None:
        self.plugin = plugin
        self.data_manager = data_manager

    async def __call__(self, request) -> Dict[str, str]:
        data = await request.json()
        inputs = data.get("inputs")
        parameters = data.get("parameters")
        logging.error("###############")
        logging.error(inputs)
        logging.error(parameters)
        logging.error("###############")

        plugin_inputs = {}
        for name, id in inputs.items():
            data = self.data_manager.load(id)
            plugin_inputs[name] = data

        # Run the (blocking, possibly GPU-bound) plugin call in an executor and await
        # it, rather than calling it inline -- Ray Serve delivers request cancellation
        # (the caller closing its connection, see analyser/server.py::abort_plugin) as
        # an asyncio.CancelledError at the *next await point*. Calling self.plugin(...)
        # directly here has no await point inside it, so a cancelled request would just
        # run to completion unnoticed. This doesn't preempt the executor thread itself
        # (Python can't do that), but it does let this replica stop waiting on it and
        # become free for the next request immediately instead of only after the
        # orphaned call finishes -- see https://docs.ray.io/en/latest/serve/http-guide.html#request-cancellation
        loop = asyncio.get_running_loop()
        try:
            results = await loop.run_in_executor(
                None,
                functools.partial(
                    self.plugin, plugin_inputs, data_manager=self.data_manager, parameters=parameters
                ),
            )
        except asyncio.CancelledError:
            logging.info("[Deployment] plugin call cancelled (client disconnected)")
            raise

        return {x: y.id for x, y in results.items()}


def app_builder(args) -> Application:
    logging.warning(args)
    data_manager = DataManager(args.get("data_path"))
    manager = AnalyserPluginManager()
    plugin = manager.build_plugin(args.get("model"), args.get("params", {}))

    return Deployment.bind(plugin, data_manager)
