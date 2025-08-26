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
    "fps": -1,
    "origin": "kickoff",
    "field_length": 105.,
    "field_width": 68.
}

requires = {
    "tracking_data": TrackingData
}

provides = {
    "pos_data": PositionData,
}

DFL_XSL = """
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" omit-xml-declaration="no" indent="yes"/>
    <xsl:strip-space elements="*"/>
    <xsl:template match="/PutDataRequest">
        <xsl:copy>
            <xsl:apply-templates select="//Positions"/>
        </xsl:copy>
    </xsl:template>
    <xsl:template match="Frame">
        <record>
            <timestamp><xsl:value-of select="@T"/></timestamp>
            <player_id><xsl:value-of select="../@PersonId"/></player_id>
            <team_id><xsl:value-of select="../@TeamId"/></team_id>
            <pos_x><xsl:value-of select="@X"/></pos_x>
            <pos_y><xsl:value-of select="@Y"/></pos_y>
            <game_section><xsl:value-of select="../@GameSection"/></game_section>
        </record>
    </xsl:template>
</xsl:stylesheet>
"""

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
        import json
        import numpy as np
        import pandas as pd
        
        from collections import defaultdict
        from datetime import timezone
        from io import StringIO
        from lxml import etree
        from pandas.api.types import is_numeric_dtype
        
        if "format" not in parameters:
            raise ValueError("'format' is required for plugin execution.")
        
        with inputs["tracking_data"] as input_data:
            with input_data.open_file() as t_data:
                # ----------------- COMPUTE
                meta_dict = defaultdict(team_ids={}, player_ids={})
                if parameters["format"] == "kinexon":
                    df = pd.read_csv(t_data, delimiter=parameters["delimiter"])
                    df = df.drop(['formatted local time', 'mapped id', 'full name', 'group id'], axis=1)
                    df["game_section"] = 0
                    df = df.rename(columns={
                        "ts in ms": "timestamp", 
                        "number": "player_id", 
                        "group name": "team_id", 
                        "x in m": "pos_x", 
                        "y in m": "pos_y"
                    })
                    df["pos_x"] = df["pos_x"].apply(lambda x: round(x, ndigits=2))
                    df["pos_y"] = df["pos_y"].apply(lambda x: round(x, ndigits=2))
                    
                    # obtain field length, field width from params for kinexon
                    PITCH_SIZE_X = parameters["field_length"]
                    PITCH_SIZE_Y = parameters["field_width"]
                    
                elif parameters["format"] == "dfl":
                    from datetime import datetime
                    # TODO: memory-efficient solution using etree iterparse -> https://lxml.de/3.2/parsing.html#iterparse-and-iterwalk
                    # ----
                    # for _, frame_set in etree.iterparse(t_data, tag="FrameSet"):
                    #     frames = [frame for frame in frame_set.iterfind("Frame")]
                    #     segment = frame_set.get("GameSection")
                    #     X = np.array([float(frame.get("X")) for frame in frames]
                    #     Y = np.array([float(frame.get("Y")) for frame in frames]
                        
                    #     frame_set.clear()
                    # ----
                    df = pd.read_xml(
                        t_data,
                        stylesheet=StringIO(DFL_XSL),
                        xpath='//record'
                    )                 
                    df[df.columns[0]] = df[df.columns[0]].apply(lambda x: int(datetime.fromisoformat(x).timestamp()*1000))
                    
                    with inputs["meta_data"] as meta_data:
                        with meta_data.open_file() as m_data:
                            tree = etree.parse(m_data)
                            root = tree.getroot()

                            PITCH_SIZE_X = float(root.findall("./MatchInformation/Environment")[0].attrib["PitchX"])
                            PITCH_SIZE_Y = float(root.findall("./MatchInformation/Environment")[0].attrib["PitchY"])
                            
                            meta_dict.update({
                                "kickoff_time": int(datetime.fromisoformat(root.findall("./MatchInformation/General")[0].attrib["KickoffTime"]).timestamp()*1000),
                                "total_time_first_half": root.findall("./MatchInformation/OtherGameInformation")[0].attrib["TotalTimeFirstHalf"],
                                "total_time_second_half": root.findall("./MatchInformation/OtherGameInformation")[0].attrib["TotalTimeSecondHalf"],
                                "playing_time_first_half": root.findall("./MatchInformation/OtherGameInformation")[0].attrib["PlayingTimeFirstHalf"],
                                "playing_time_second_half": root.findall("./MatchInformation/OtherGameInformation")[0].attrib["PlayingTimeSecondHalf"]
                            })
                else:
                    raise ValueError("'format' has to be either one of ['dfl', 'kinexon'], other formats are not supported yet for conversion.")
            
                # ---- Data/Coords normalization
                # origin (0,0)^T is at the kickoff, i.e. x values left of kickoff are negative & y values below kickoff are engative
                if parameters["origin"] == "kickoff":  
                    MAX_X = PITCH_SIZE_X / 2.0
                    MAX_Y = PITCH_SIZE_Y / 2.0
                    df["pos_x"] = (df["pos_x"] + MAX_X) / PITCH_SIZE_X
                    df["pos_y"] = 1.0 - ((df["pos_y"] + MAX_X) / PITCH_SIZE_Y)  # correct for inverted Y-axis
                    
                # origin (0,0)^T is at the bottom left, i.e. all values on both axes are >= 0
                elif parameters["origin"] == "bottom_left":
                    MAX_X = PITCH_SIZE_X
                    MAX_Y = PITCH_SIZE_Y
                    df["pos_x"] = df["pos_x"] / PITCH_SIZE_X  # normalize to a range of [0,1]
                    df["pos_y"] = (MAX_Y - df["pos_y"]) / PITCH_SIZE_Y  # inverted Y-axis, images start at top left corner
            
                # ---- FPS filtering
                unique_timestamps = df[df.columns[0]].unique()  # all unique timestamps, in order of appearance
                
                if "kickoff_time" in meta_dict:
                    meta_dict["kickoff_time"] = int(meta_dict["kickoff_time"] - unique_timestamps.min())
                
                # df[df.columns[0]] = df[df.columns[0]].apply(lambda x: x - unique_timestamps.min())
                # NOTE: checks if specified fps parameter is in an applicable range
                freq = unique_timestamps[1] - unique_timestamps[0]
                origin_fps = 1000/freq
                actual_fps = origin_fps
                if parameters["fps"] > 0:
                    if parameters["fps"] > origin_fps:
                        raise ValueError("framerate needs to be set lower than the original framerate.")
                    else:
                        actual_fps = parameters["fps"]
                        step_size = np.int32(origin_fps/actual_fps)  # compute step size for filtering
                        selected_timestamps = unique_timestamps[::step_size]
                        df = df[df[df.columns[0]].isin(selected_timestamps)]  # keeps all rows where 'timestamp' is in the selected list
                # else:
                #    raise ValueError("framerate needs to be larger than zero.")
                
                meta_dict["fps"] = actual_fps
                
                df[df.columns[0]] = df[df.columns[0]] - unique_timestamps.min()  # reset timestamps to zero    
            
                # map player and team ids
                if not is_numeric_dtype(df["team_id"].dtype):
                    unique_teams = df["team_id"].unique()
                    for i, team_label in enumerate(unique_teams, start=1):
                        # df.loc[df["team_id"] == team_label, "team_id"] = col
                        df["team_id"] = df["team_id"].replace(team_label, i)
                        meta_dict["team_ids"].update({ i : team_label})

                if not is_numeric_dtype(df["player_id"].dtype):
                    unique_players = df["player_id"].unique()
                    for i, player_label in enumerate(unique_players, start=1):
                        df["player_id"] = df["player_id"].replace(player_label, i)
                        meta_dict["player_ids"].update({ i : player_label})
                    
                # TODO: do this while XML parsing?
                if parameters["format"] == "dfl":
                    df["game_section"] = df["game_section"].replace("firstHalf", 1)
                    df["game_section"] = df["game_section"].replace("secondHalf", 2)
                
                grouped_dict = df.groupby(
                    'timestamp', group_keys=False
                ).apply(
                    # lambda x: x.to_dict(orient='records'),
                    # lambda x: x.to_numpy().tolist(), # NOTE: numpy solution, faster but upcasts every value to float
                    lambda x: [list(row) for row in x.itertuples(index=False)],
                    include_groups=False
                )
                del df
                py_dict = grouped_dict.to_dict()
                del grouped_dict
                # -----------------
        # ----------------- OUTPUT
        with data_manager.create_data("PositionData") as pos_data:
            pos_data.name = "pos_data"
            pos_data.tracking_data_id = parameters.get('tracking_data_id')  # Required field
            pos_data.meta_data = json.dumps(meta_dict)
            pos_data.pos = json.dumps(py_dict)

            self.update_callbacks(callbacks, progress=1.0)
        
        return {"pos_data": pos_data}
        