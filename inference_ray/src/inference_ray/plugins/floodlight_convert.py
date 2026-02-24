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

        from floodlight.models.geometry import CentroidModel
        from floodlight.models.kinematics import DistanceModel, VelocityModel
        from floodlight.models.kinetics import MetabolicPowerModel

        if "format" not in parameters:
            raise ValueError("'format' is required for plugin execution.")

        logging.error(inputs)
        # ----------------- PARSING
        with inputs["tracking_data"] as input_data: # TrackingData
            with input_data.open_file() as t_data: # ZipExtFile
                if parameters["format"] == "kinexon":
                    with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv') as tmp_data:
                        tmp_data.write(t_data.read())
                        # NOTE: returns: List[XY]
                        pos = read_position_data_csv(tmp_data.name, delimiter=parameters["delimiter"])
                        logging.error(type(pos))
                        for p_ in pos:
                            logging.error(f'{type(p_)} - {p_.xy.shape} - {p_.framerate}')
                            sampled_data = p_.xy
                elif parameters["format"] == "dfl":
                    with tempfile.NamedTemporaryFile(mode='w+b', suffix='.xml') as tmp_data:
                        tmp_data.write(t_data.read())
                        with inputs["meta_data"] as meta_data:
                            with meta_data.open_file() as m_data:
                                with tempfile.NamedTemporaryFile(mode='w+b', suffix='.xml') as tmp_meta:
                                    tmp_meta.write(m_data.read())
                                    # NOTE: returns: Tuple[
                                        # Dict[str, Dict[str, XY]],
                                        # Dict[str, Code],
                                        # Dict[str, Code],
                                        # Dict[str, Teamsheet],
                                        # Pitch
                                    # ]
                                    data, po, bs, ts, pitch = read_position_data_xml(tmp_data.name, tmp_meta.name)
                                    logging.error(f'{type(data)} - {type(po)} - {type(bs)} - {type(ts)} - {type(pitch)}')
                                    # pID_dict, no_frames, framerate, t_null = get_meta_data(m_data, parameters["delimiter"])
                                    for key in data:
                                        logging.error(key) # 'firstHalf', 'secondHalf'
                                        for pos_data in data[key].items():
                                            logging.error(type(pos_data))
                                            logging.error(pos_data[0]) # 'Home', 'Away', 'Ball'
                                            logging.error(f'{pos_data[1]} - {type(pos_data[1].xy.shape)}') # XY object, XY.xy -> np.NDarray
                                    sampled_data = data['firstHalf']['Home'].xy
                                    logging.error(sampled_data)
        # ----------------- COMPUTE
        # TODO: KPI computation
        xy_pos = sampled_data
        meta_data = {"some_meta_data": 1337}
        DistMod = DistanceModel()
        VelMod = VelocityModel()
        MetPowMod = MetabolicPowerModel()
        CentMod = CentroidModel()

        kpi_dict = {}
        for half in ["firstHalf", "secondHalf"]:
            for team in ["Home", "Away"]:
                DistMod.fit(xy[half][team])
                VelMod.fit(xy[half][team])
                MetPowMod.fit(xy[half][team])
                CentMod.fit(xy[half][team])

            kpi_dict[f'distance_covered_{half}_{team}'] = np.array(DistMod.cumulative_distance_covered())
            kpi_dict[f'max_velocity_{half}_{team}'] = np.nanmax(VelMod.velocity(), axis=0).round(2)
            kpi_dict[f'metabolic_power_{half}_{team}'] = np.array(MetPowMod.metabolic_power())
            kpi_dict[f'centroid_{half}_{team}'] = CentMod.centroid().xy
        # ----------------- OUTPUT
        # TODO: specify output type based on what you need, see "packages/data/src/data/plugins/tracking_data.py"
        with data_manager.create_data("FloodlightData") as fl_data:
            fl_data.name = "fl_data"
            fl_data.tracking_data_id = parameters.get('tracking_data_id')
            #fl_data.meta_data = json.dumps(meta_data)
            fl_data.kpis = kpi_dict
            fl_data.xy_pos = xy_pos

            self.update_callbacks(callbacks, progress=1.0)
        return {"fl_data": fl_data}
