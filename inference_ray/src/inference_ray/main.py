import asyncio
import functools
import logging
from ray import serve
from typing import Dict
from ray.serve import Application

from data import DataManager
from inference_ray.plugin import (
    AnalyserPluginManager,
    AnalyserPlugin,
    ValkeyProgressCallback,
)


@serve.deployment
class Deployment:
    def __init__(self, plugin: AnalyserPlugin, data_manager: DataManager) -> None:
        self.plugin = plugin
        self.data_manager = data_manager

    async def __call__(self, request) -> Dict[str, str]:
        data = await request.json()
        inputs = data.get("inputs")
        parameters = data.get("parameters")
        job_id = data.get("job_id")
        logging.error("###############")
        logging.error(inputs)
        logging.error(parameters)
        logging.error("###############")

        # NOTE: This callback pushes the progress reported by the plugin (self.update_callbacks())
        # to valkey, referenced via job_id. Analyser reads it from GetPluginStatus()..
        callbacks = [ValkeyProgressCallback(job_id)] if job_id else None

        plugin_inputs = {}
        for name, id in inputs.items():
            data = self.data_manager.load(id)
            plugin_inputs[name] = data

        # NOTE: Ray Deployment now uses asynchronous execution & a bounded executor to ensure plugins cooperate with cancel_event.
        # Moved blocking plugin execution into an executor.
        # When the analyser closes its HTTP connection --> Ray Serve detects the request cancellation.
        # Request handler stops waiting for the plugin result.
        # However, does not stop the executor thread itself.
        # Plugin call may continue running in the executor unless the plugin has its own cancellation mechanism.
        # https://docs.ray.io/en/latest/serve/http-guide.html#request-cancellation
        
        loop = asyncio.get_running_loop()
        try:
            results = await loop.run_in_executor(
                None,
                functools.partial(
                    self.plugin,
                    plugin_inputs,
                    data_manager=self.data_manager,
                    parameters=parameters,
                    callbacks=callbacks,
                ),
            )
        except asyncio.CancelledError:
            logging.info("[Deployment] plugin call cancelled (client disconnected)")
            raise

        return {x: y.id for x, y in results.items()}


def app_builder(args) -> Application:
    # logging.warning(args)
    data_manager = DataManager(args.get("data_path"))
    manager = AnalyserPluginManager()
    plugin = manager.build_plugin(args.get("model"), args.get("params", {}))

    return Deployment.bind(plugin, data_manager)
