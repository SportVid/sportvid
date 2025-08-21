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
            with input_data.open_file() as t_data:
                if parameters["format"] == "kinexon":
                    # NOTE: returns List[XY]
                        # XY:
                            # xy: np.ndarray
                            # ---
                            # Full data array containing x- and y-coordinates, 
                            # where each player's coordinates occupy two consecutive columns.
                            #
                            # framerate: int, optional
                            # ---
                            #
                            # direction: {'lr', 'rl'}, optional
                            # ---
                            # Playing direction of players in data fragment, should be either
                            # 'lr' (left-to-right) or 'rl' (right-to-left).
                    pos_data = read_position_data_csv(t_data, delimiter=parameters["delimiter"])
                    logging.error(type(pos_data))
                    # meta data handling
                    if inputs["meta_data"]:
                        with inputs["meta_data"] as meta_data:
                            with meta_data.open_file() as m_data:
                                # NOTE: returns Tuple[Dict[str, Dict[str, List[str]]], int, int, int]
                                pID_dict, no_frames, framerate, t_null = get_meta_data(m_data, _delimiter=';')
                # --------------------------------       
                elif parameters["format"] == "dfl":
                    with inputs["meta_data"] as meta_data:
                        with meta_data.open_file() as m_data:
                            # --------------
                            # NOTE returns: Tuple[Dict[str, Dict[str, XY]], Dict[str, Code], Dict[str, Code], Dict[str, Teamsheet], Pitch]
                                # data_objects - Tuple of (nested) floodlight core objects with shape (xy_objects, possession_objects, ballstatus_objects, teamsheets, pitch)
                                    # xy_objects is a nested dictionary containing XY objects for each team and segment of the form:
                                    #   xy_objects[segment][team] = XY. For a typical league match with two halves and teams this dictionary looks like:
                                    #   {'firstHalf': {'Home': XY, 'Away': XY}, 'secondHalf': {'Home': XY, 'Away': XY}}.
                                        # XY: ...
                                    # ---------
                                    # possession_objects is a dictionary containing Code objects with possession information (home or away) 
                                    #   for each segment of the form possession_objects[segment] = Code.
                                        # Code:
                                            # code: np.ndarray
                                            # ---
                                            # One-dimensional array with codes describing a sequence of play.
                                            # name: str
                                            # ---
                                            # Name of encoded game state (e.g. 'possession').
                                            # definitions: dict, optional
                                            # ---
                                            # Dictionary of the form {token: definition} where each code category is defined or explained.
                                            # framerate: int, optional
                                            # ---
                                            # Temporal resolution of data in frames per second/Hertz.
                                    # ---------
                                    # ballstatus_objects is a dictionary containing Code objects with ballstatus information (dead or alive) 
                                    #   for each segment of the form ballstatus_objects[segment] = Code.
                                        # Code: ...
                                     # ---------
                                    # teamsheets is a dictionary containing Teamsheet objects for each team of the form teamsheets[team] = Teamsheet.
                                        # Teamsheet:
                                            # teamsheet: pd.DataFrame
                                            # ---
                                            # DataFrame containing rows of players and columns of respective properties.
                                    # ---------
                                    # pitch is a Pitch object corresponding to the data.
                                        # Pitch:
                                            # xlim: Tuple[Numeric, Numeric]
                                            # ---
                                            # Limits of pitch boundaries in longitudinal direction. This tuple has the form (x_min, x_max) and delimits 
                                            # the length of the pitch (not of any actual data) within the coordinate system.
                                            # ylim: Tuple[Numeric, Numeric]
                                            # ---
                                            # unit: {'m', 'cm', 'percent', 'normed'}
                                            # ---
                                            # boundaries: str one of ['fixed', 'flexible']
                                            # ---
                                            # length: Numeric, optional
                                            # ---
                                            # width: Numeric, optional
                                            # ---
                                            # sport: str, optional one of ["football", "handball"]     
                            # --------------
                            data_objects, possession_objects, ballstatus_objects, teamsheets, pitch = read_position_data_xml(t_data, m_data)
                            logging.error(type(data_objects))
                else:
                    raise ValueError(f"provided format is not supported.")        
        # ----------------- COMPUTE
        # TODO: KPI computation
        # ----------------- OUTPUT
        # TODO: define correct output type.
        with data_manager.create_data("FloodlightData") as fl_data:
            fl_data.name = "fl_data"
            fl_data.tracking_data_id = parameters.get('tracking_data_id') 
            fl_data.meta_data = {"some_data": 1337}
            fl_data.xy_pos = np.zeros(shape=(2,1), dtype=np.float32)
            
            self.update_callbacks(callbacks, progress=1.0)
        return {"fl_data": fl_data}