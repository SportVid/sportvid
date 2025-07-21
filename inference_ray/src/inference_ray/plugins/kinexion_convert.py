from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

import logging
from data import ScalarData
from data import DataManager, Data

from typing import Callable, Dict

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {}

requires = {} # TODO

provides = {
    "converted_kinexion_csv": ScalarData, # TODO: type
}


@AnalyserPluginManager.export("kinexion_convert")
class KinexionConvert(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]:

        # NOTE: imports für die eigentliche Logik hier definieren, könnte auch ein Import der 
        # Floodlight library sein, solange das Plugin korrekt registriert ist und alle Abhängikeiten beim
        # bauen        
        # ----------------- IMPORTS
        import json
        import numpy as np
        import pandas as pd
        # -----------------

        # ----------------- DATEN LADEN
        logging.debug(f"Parameters: {parameters}")
        if "some_data" not in parameters:
            raise ValueError("some_data is required for the conversion.")
        
        kinexion_data = json.loads(parameters["some_data"])
        # NOTE: value checks hier empfohlen
        # -----------------
        
        # ----------------- COMPUTE
        # TODO: Irgendwelche Berechnungen/Conversions der Eingabedaten durchführen
        # -----------------
        x = 13
        y = 37

        # ----------------- OUTPUT
        # NOTE: Typ von create_data an den Output anpassen
        with data_manager.create_data("ScalarData") as output_data:
            output_data.x = x.tolist()
            output_data.y = y.tolist()
            output_data.name = "converted_kinexion_csv"
            output_data.time = [0.0]  # Required field
            output_data.delta_time = 1.0  # Required field
            
            self.update_callbacks(callbacks, progress=1.0)
            return {"converted_kinexion_csv": output_data}
        # ----------------- OUTPUT