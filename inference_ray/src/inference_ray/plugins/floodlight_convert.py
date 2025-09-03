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
        import json
        import os
        import numpy as np
        import pandas as pd
        import tempfile
        import zipfile
        
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

        with inputs["tracking_data"] as input_data:
            logging.error(type(input_data))
            with input_data.open_file() as t_data:
                logging.error(type(t_data))
            with input_data.load_file_from_stream() as t_data:
                logging.error(type(t_data))
        
        # with tempfile.TemporaryDirectory() as t_temp_dir:
        #     with inputs["tracking_data"] as input_data:
        #         with input_data.open_file() as t_data:
        #             ex_t_data = t_data.extractall(path=t_temp_dir)
        #             ex_t_data = os.path.join(t_temp_dir, ex_t_data)
        #             logging.error(type(t_data))
        #             if parameters["format"] == "kinexon":
        #                 pos_data = read_position_data_csv(t_data, parameters["delimiter"])
        #                 # TODO: read_position_data_csv requires path to meta data file... 
        #                 #   https://floodlight.readthedocs.io/en/latest/_modules/floodlight/io/kinexon.html#read_position_data_csv
        #                 logging.error(type(pos_data))
        #                 # meta data handling
        #                 if inputs["meta_data"]:
        #                     with inputs["meta_data"] as meta_data:
        #                         with meta_data.open_file() as m_data:
        #                             # NOTE: returns Tuple[Dict[str, Dict[str, List[str]]], int, int, int]
        #                             pID_dict, no_frames, framerate, t_null = get_meta_data(m_data, parameters["delimiter"])
        #             # --------------------------------       
        #             elif parameters["format"] == "dfl":
        #                 with tempfile.TemporaryDirectory() as m_temp_dir:
        #                     with inputs["meta_data"] as meta_data:
        #                         with meta_data.open_file() as m_data:
        #                             ex_m_data = m_data.extractall(path=m_temp_dir)
        #                             ex_m_data = os.path.join(m_temp_dir, ex_m_data)
        #                             data_objects, possession_objects, ballstatus_objects, teamsheets, pitch = read_position_data_xml(ex_t_data, ex_m_data)
        #                             logging.error(type(data_objects))
        #             else:
        #                 raise ValueError(f"provided format is not supported.")        
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