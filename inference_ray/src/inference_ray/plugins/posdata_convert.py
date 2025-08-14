import logging

from typing import Callable, Dict

from data import PositionData, TrackingData
from data import DataManager, Data

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

# Config params are passed during the building process of a plugin
default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

# Define parameters that are required during the runtime of a plugin
default_parameters = {
    "delimiter": ";",
    "fps": None
}

requires = {
    "tracking_data": TrackingData
}

provides = {
    "pos_data": PositionData,
}


@AnalyserPluginManager.export("posdata_convert")
class PosDataConvert(
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
        from io import StringIO
        from lxml import etree
        # -----------------

        # ----------------- DATA LOADING
        logging.error(f'[PLUGIN]\tinputs: {inputs}')
        logging.error(f'[PLUGIN]\tparams: {parameters}')
        
        if "format" not in parameters:
            raise ValueError("'format' is required for plugin execution.")

        # TODO: Create a JSON with the same format, no matter the format.
        with inputs["tracking_data"] as input_data:
            with input_data.open_file() as t_data:
                # ----------------- COMPUTE
                if parameters["format"] == "kinexon":
                    df = pd.read_csv(t_data, delimiter=parameters["delimiter"])
                    unique_timestamps = df[df.columns[0]].unique()  # all unique timestamps, in order of appearance
                    
                    # NOTE: checks if specified fps parameter is in an applicable range
                    freq = unique_timestamps[1] - unique_timestamps[0] 
                    origin_fps = 1000/freq
                    logging.error(origin_fps)
                    
                    if parameters["fps"] > 0:
                        logging.error(parameters["fps"])
                        if parameters["fps"] > origin_fps:
                            raise ValueError("framerate needs to be lower than the original framerate of the tracking data.")

                    step_size = np.int32(origin_fps/parameters["fps"]) # compute step size for filtering
                    selected_timestamps = unique_timestamps[::step_size]
                    df_downsampled = df[df[df.columns[0]].isin(selected_timestamps)]  # keeps all rows where 'timestamp' is in the selected list
                    logging.error(df_downsampled)
                elif parameters["format"] == "dfl":
                    # -------------> DFL XML PARSING
                    # FrameSet: PersonId
                    # Frame: N T X Y
                    
                    # from io import StringIO
                    # from lxml import etree
                    
                    # xml_doc = etree.parse("/home/ak/in.xml")
                    # xslt_doc = etree.parse("/home/ak/style.xls")
                    # transform = etree.XSLT(xslt_doc)
                    # result_tree = transform(xml_doc)
                    # print(etree.tostring(result_tree, pretty_print=True).decode())
                    
                    # df = pd.read_xml(
                    #     StringIO(xml_),
                    #     stylesheet=StringIO(xsl_),
                    #     xpath='//record'
                    # )
                    # print(df)
                    
                    # -------------> TEST DATA
                    # <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    # <PutDataRequest RequestId="6dbe87b3-5d27-4788-9824-a5251b5ebeb0"
                    #     MessageTime="2025-04-10T05:41:28.500+00:00" TransmissionComplete="true"
                    #     TransmissionSuspended="false">
                    #     <Positions EventTime="2025-04-09T17:01:23.648+00:00">
                    #         <MetaData MatchId="DFL-MAT-J040TC" Type="pitch-size">
                    #             <PitchSize X="105.00" Y="68.00" />
                    #         </MetaData>
                    #         <FrameSet GameSection="firstHalf" MatchId="DFL-MAT-J040TC" TeamId="DFL-CLU-00000O"
                    #             PersonId="DFL-OBJ-J01P2M">
                    #             <Frame N="10000" T="2025-04-09T17:01:23.648+00:00" X="-36.68" Y="1.20" D="0.00"
                    #                 S="-9999.00" A="-9999.00" M="1" />
                    #             <Frame N="10001" T="2025-04-09T17:01:23.688+00:00" X="-36.68" Y="1.20" D="0.00"
                    #                 S="-9999.00" A="-9999.00" M="1" />
                    #         </FrameSet>
                    #         <FrameSet GameSection="firstHalf" MatchId="DFL-MAT-J040TC" TeamId="DFL-CLU-00000O"
                    #             PersonId="DFL-OBJ-J01P2A">
                    #             <Frame N="10000" T="2025-04-09T17:01:23.648+00:00" X="-36.68" Y="1.20" D="0.00"
                    #                 S="-9999.00" A="-9999.00" M="1" />
                    #             <Frame N="10001" T="2025-04-09T17:01:23.688+00:00" X="-36.68" Y="1.20" D="0.00"
                    #                 S="-9999.00" A="-9999.00" M="1" />
                    #         </FrameSet>
                    #     </Positions>
                    # </PutDataRequest>
                    
                    # -------------> STYLE FILE
                    dfl_xsl = """<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
                    <xsl:output method="xml" omit-xml-declaration="no" indent="yes"/>
                    <xsl:strip-space elements="*"/>
                    <xsl:template match="/PutDataRequest">
                        <xsl:copy>
                            <xsl:apply-templates select="//Positions"/>
                        </xsl:copy>
                    </xsl:template>
                    <xsl:template match="Frame">
                        <record>
                            <frame_id><xsl:value-of select="@N"/></frame_id>
                            <player_id><xsl:value-of select="../@PersonId"/></player_id>
                            <time_t><xsl:value-of select="@T"/></time_t>
                            <pos_x><xsl:value-of select="@X"/></pos_x>
                            <pos_y><xsl:value-of select="@Y"/></pos_y>
                        </record>
                    </xsl:template>
                    </xsl:stylesheet>"""
                    # TODO: https://pandas.pydata.org/docs/user_guide/io.html#io-read-xml
                    # memory-efficient solution using lxml’s iterparse and etree’s iterparse
                    df = pd.read_xml(
                        input_data,
                        stylesheet=StringIO(dfl_xsl), 
                        xpath='//record'
                    )
                    logging.error(df)
                    # TODO: FPS filtering
                    
                else:
                    raise ValueError("'format' has to be either one of ['dfl', 'kinexon'], other formats are not supported yet for conversion.")
                # -----------------
        # ----------------- OUTPUT
        with data_manager.create_data("PositionData") as pos_data:
            pos_data.name = "pos_data"
            pos_data.ref_id = parameters.get('tracking_data_id')  # Required field
            pos_data.delta_time = 1.0  # Required field
            pos_data.pos = 'TODO' # TODO: use actual JSON-ified string
      
            self.update_callbacks(callbacks, progress=1.0)
        
        return {"pos_data": pos_data}
        # -----------------
        