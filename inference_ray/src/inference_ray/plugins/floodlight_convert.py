import logging

from typing import Callable, Dict

from data import FloodlightData, TrackingData
from data import DataManager, Data

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

# Config params are passed during the building process of a plugin
default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

# Define parameters that are required uring the runtime of a plugin
default_parameters = {
    "delimiter": ";"
}

requires = {
    "tracking_data": TrackingData
}

provides = {
    "floodlight_data": FloodlightData,
}

@AnalyserPluginManager.export("floodlight_convert")
class FloodlightConvert(
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
        # ----------------- IMPORTS
        import numpy as np
        import pandas as pd
        
        # from floodlight.core import (
        #     code,
        #     events,
        #     pitch,
        #     teamsheet,
        #     xy
        # )
        # from floodlight.utils.types import Numeric
        from floodlight.io.kinexon import (
            get_meta_data, read_position_data_csv
        )
        from floodlight.io.dfl import (
            read_event_data_xml, 
            read_teamsheets_from_mat_info_xml, 
            read_pitch_from_mat_info_xml, 
            read_position_data_xml
        )
        # ----------------- DATA LOADING
        if "format" not in parameters:
            raise ValueError("'format' is required for plugin execution.")
        
        with inputs["tracking_data"] as input_data:
            with input_data.open_file() as t_data:
                if parameters["format"] == "kinexon":
                    knx_data = read_position_data_csv(t_data, delimiter=parameters["delimiter"])
                # TODO: meta data handling for kinexon?
                # if parameters["meta_data_provided"]:
                #     with meta_data.open_file() as meta_data:
                            # NOTE: returns Tuple[Dict[str, Dict[str, List[str]]], int, int, int]
                #           pID_dict, no_frames, framerate, t_null = get_meta_data(meta_data, _delimiter=';')
                elif parameters["format"] == "dfl":
                #    
                # else: 
                # ----------------- COMPUTE
                kinexon_df = pd.read_csv(t_data, sep=';')
                logging.error(kinexon_df)
                # xy_col = kinexon_df.columns.values.tolist()[-3:-1]
                xy_col = kinexon_df.columns.values.tolist()[-2::]
                logging.error(xy_col)
                xy_slice = kinexon_df[xy_col][:100]
                np_position_data = xy_slice.to_numpy(dtype=np.float32)
                logging.error(f'[PLUGIN]\tkinexon data frame: {kinexon_df.shape}, {kinexon_df.columns.values.tolist()}')
                logging.error(f'[PLUGIN]\tnumpy pos data: {np_position_data.shape}')
                # -----------------
        # ----------------- OUTPUT
        with data_manager.create_data("FloodlightData") as fl_data:
            fl_data.name = "fl_data"
            fl_data.tracking_data_id = parameters.get('tracking_data_id') 
            fl_data.meta_data = 1337  # TODO
            fl_data.xy_pos = np_position_data.copy()
            
            self.update_callbacks(callbacks, progress=1.0)
        return {"pos_data": fl_data}
        # -----------------
        