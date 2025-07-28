from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

import logging
from data import PositionData#, PositionsData
from data import DataManager, Data

from typing import Callable, Dict

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {
    # TODO
}

requires = {
    # TODO
}

provides = {
    "converted_kinexon_data": PositionData, # PositionsData
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
        super().__init__(config, **kwargs)

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]:

        # NOTE: Imports definieren; müssen vorher in 'deploy.yml' & 'deploy.cuda.yml' registriert sein      
        # ----------------- IMPORTS
        import numpy as np
        import pandas as pd
        import floodlight as fl
        # -----------------

        # ----------------- DATA LOADING
        logging.error(f'[PLUGIN]\tinputs: {inputs}')
        logging.error(f'[PLUGIN]\tparams: {parameters}')
        
        if "tracking_data_db" not in parameters:
            raise ValueError("'tracking_data_db' is required for the conversion.")
        
        with inputs["tracking_data"] as input_data:
            with input_data.open_file() as t_data:        
                kinexon_df = pd.read_csv(t_data, sep=';')
                xy_col = kinexon_df.columns.values.tolist()[-3:-1]
                xy_slice = kinexon_df[xy_col][:100]
                np_pos_data = xy_slice.to_numpy(dtype=np.float32)
                logging.error(f'[PLUGIN]\tkinexon data frame: {kinexon_df.shape}, {kinexon_df.columns.values.tolist()}')
                logging.error(f'[PLUGIN]\tnumpy pos data: {np_pos_data.shape}')
                # ----------------- COMPUTE
                # TODO: Logik
                # -----------------

        # ----------------- OUTPUT
        # NOTE: Ausgabe definieren; TYPE von create_data('TYPE') an den Output anpassen
        with data_manager.create_data("PositionData") as pos_data:
            # pos_data.name = "pos_data"
            pos_data.ref_id = parameters.get('tracking_data_db')  # Required field
            pos_data.delta_time = 1.0  # Required field
            pos_data.pos = np_pos_data.copy()
            
            self.update_callbacks(callbacks, progress=1.0)
            logging.error(f'[PLUGIN]\tpos_data: {pos_data}')
            return {"pos_data": pos_data}
        # -----------------