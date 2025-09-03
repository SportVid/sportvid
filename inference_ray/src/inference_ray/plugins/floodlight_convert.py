import logging
import tempfile

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
        import json
        import os
        import numpy as np
        import pandas as pd

        from floodlight.io.kinexon import (
            get_meta_data, 
            read_position_data_csv
        )
        from floodlight.io.dfl import (
            # read_event_data_xml, 
            # read_teamsheets_from_mat_info_xml, 
            # read_pitch_from_mat_info_xml, 
            read_position_data_xml
        )
        # ----------------- DATA LOADING
        if "format" not in parameters:
            raise ValueError("'format' is required for plugin execution.")

        with inputs["tracking_data"] as input_data: # TrackingData   
            with input_data.open_file() as zip_data: # ZipExtFile
                # import inspect
                # logging.error(inspect.signature(read_position_data_csv))
                # pos_data = read_position_data_csv(zip_data, parameters["delimiter"])
                with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as tmp_file:
                    tmp_file.write(zip_data.read())
                    tmp_file_path = tmp_file.name
                    logging.error(tmp_file_path)
                    # TODO: see what is wrong with that shitty lib...
                    
                    df = pd.read_csv(tmp_file_path, delimiter=parameters["delimiter"])
                    logging.error(df)
                    pos_data = read_position_data_csv(tmp_file_path)
        
                    # d_o, p_o, bs_o, ts, pitch = read_position_data_xml(ex_t_data, ex_m_data)
                    # meta data handling
                    # if inputs["meta_data"]:
                    #     with inputs["meta_data"] as meta_data:
                    #         with meta_data.open_file() as m_data:
                    #             # NOTE: returns Tuple[Dict[str, Dict[str, List[str]]], int, int, int]
                    #             pID_dict, no_frames, framerate, t_null = get_meta_data(m_data, parameters["delimiter"])
                    # --------------------------------       
                    if parameters["format"] == "kinexon": pass
                    elif parameters["format"] == "dfl": pass   
        # ----------------- COMPUTE
        # TODO: KPI computation
        xy_pos = np.zeros(shape=(2,1), dtype=np.float32)
        meta_data = {"some_data": 1337}
        # ----------------- OUTPUT
        # TODO: define correct output type
        with data_manager.create_data("FloodlightData") as fl_data:
            fl_data.name = "fl_data"
            fl_data.tracking_data_id = parameters.get('tracking_data_id') 
            fl_data.meta_data = json.dumps(meta_data)
            fl_data.xy_pos = xy_pos
            
            self.update_callbacks(callbacks, progress=1.0)
        return {"fl_data": fl_data}