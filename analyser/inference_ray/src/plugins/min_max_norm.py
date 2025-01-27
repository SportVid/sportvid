from analyser.inference.plugin import AnalyserPlugin, AnalyserPluginManager
from analyser.data import ScalarData, ImageEmbeddings

import logging
import numpy as np
from analyser.data import DataManager, Data

from typing import Callable, Optional, Dict


default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {}

requires = {
    "scalar": ScalarData,
}

provides = {
    "scalar": ScalarData,
}


@AnalyserPluginManager.export("min_max_norm")
class MinMaxNorm(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        self.host = self.config["host"]
        self.port = self.config["port"]

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]:
        with inputs["scalar"] as scalar_data, data_manager.create_data("ScalarData") as output_data:
            y = scalar_data.y

            if (np.max(y) - np.min(y)) >= 0.01:
                y = (y - np.min(y)) / (np.max(y) - np.min(y))

            output_data.y = y
            output_data.time = scalar_data.time
            output_data.delta_time = scalar_data.delta_time
            return {"scalar": output_data}
