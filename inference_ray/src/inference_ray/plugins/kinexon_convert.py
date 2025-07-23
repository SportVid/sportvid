from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

import logging
from data import PositionsData
from data import DataManager, Data

from typing import Callable, Dict

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {}

requires = {
    
}

provides = {
    "converted_kinexon_data": PositionsData, # PositionData or PositionsData ???
}


@AnalyserPluginManager.export("kinexon_convert")
class KinexonConvert(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    def __init__(self, config=None, **kwargs):
        logging.debug('calling __init__ of KinexonConvert()')
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
        # TODO: import flashlight as fl
        # -----------------

        # ----------------- DATA LOADING
        logging.debug(f'Inputs: {inputs}')
        logging.debug(f"Parameters: {parameters}")
        
        #if "some_data" not in parameters:
        #    raise ValueError("some_data is required for the conversion.")
        # kinexon_data = json.loads(parameters["some_data"])
        
        # NOTE: Value checks falls nötig
        # -----------------
        
        # ----------------- COMPUTE
        # TODO: Irgendwelche Berechnungen/Conversions der Eingabedaten durchführen
        # -----------------

        # ----------------- OUTPUT
        # NOTE: Typ von create_data an den Output anpassen
        with data_manager.create_data("PositionsData") as pos_data:
            pos_data.name = "converted_kinexon_data"
            pos_data.time = [0.0]  # Required field
            pos_data.delta_time = 1.0  # Required field
            pos_data.pos = np.zeros(shape=[100,22*2], dtype=np.float32)
            
            self.update_callbacks(callbacks, progress=1.0)
            return {"converted_kinexon_data": pos_data}
        # -----------------