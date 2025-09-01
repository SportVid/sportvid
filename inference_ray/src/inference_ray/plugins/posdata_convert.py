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
            <game_section><xsl:value-of select="../@GameSection"/></game_section>
            <pos_x><xsl:value-of select="@X"/></pos_x>
            <pos_y><xsl:value-of select="@Y"/></pos_y>
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
        pd.set_option('future.no_silent_downcasting', True)
        
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
                    
                    # rearrange indices to keep it consistent with dfl
                    cols = list(df.columns)
                    pos_x, pos_y, gs = cols.index('pos_x'), cols.index('pos_y'), cols.index('game_section')
                    cols[pos_x], cols[pos_y], cols[gs] = cols[gs], cols[pos_x], cols[pos_y]
                    df = df[cols]
                    
                    df["pos_x"] = df["pos_x"].apply(lambda x: round(x, ndigits=2))
                    df["pos_y"] = df["pos_y"].apply(lambda x: round(x, ndigits=2))
                    
                    # obtain field length, field width from params for kinexon
                    PITCH_SIZE_X = parameters["field_length"]
                    PITCH_SIZE_Y = parameters["field_width"]
                    
                    if not parameters["team_id_ball"]:
                        raise ValueError("Please specify 'team_id_ball' for kinexon tracking data.")
                    
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
                    # transform timestamps            
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

                # Remove empty columns
                df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

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
            
                if "kickoff_time" in meta_dict:
                    meta_dict["kickoff_time"] = int(meta_dict["kickoff_time"] - unique_timestamps.min())

                # ---- FPS filtering: checks if specified fps parameter is in an applicable range
                unique_timestamps = df[df.columns[0]].unique()  # all unique timestamps, in order of appearance
                # freq = unique_timestamps[1] - unique_timestamps[0]
                diffs = unique_timestamps[1:] - unique_timestamps[:-1]
                freq = diffs.mean()
                origin_fps = int(np.rint(1000./freq))
                actual_fps = origin_fps
                
                step_size = 0
                if parameters["fps"] > 0:
                    if parameters["fps"] > origin_fps:
                        raise ValueError("framerate needs to be set lower than the original framerate.")
                    else:
                        actual_fps = parameters["fps"]
                        
                        pos_downsample_fps = []
                        for i in range(origin_fps-1,0,-1):
                            if origin_fps % i == 0: pos_downsample_fps.append(i)
                        pos_fps_npy = np.asarray(pos_downsample_fps)
                        idx = (np.abs(pos_fps_npy - actual_fps)).argmin()
                        actual_fps = pos_fps_npy[idx]
                        meta_dict["fps"] = actual_fps
                        
                        step_size = np.int8(origin_fps/actual_fps)  # compute step size for filtering
                        # ---- calc err. of linear interpolation
                        dev = list()
                        df_players = df.groupby(
                            'player_id', group_keys=False
                        ).apply(
                            lambda x: x.to_numpy(), 
                            include_groups=False
                        )
                        actualp, subsampled = None, None
                        for player_id in df["player_id"].unique():
                            actualp = np.array(df_players[player_id][:,3:], dtype=np.float32)  # [[x,y]]
                            ap_idx = np.arange(actualp.shape[0])
                            subs_idx = ap_idx[::step_size]
                            N = actualp.shape[0]; M = actualp.shape[1]

                            subsampled = actualp[::step_size]
                            interp = np.zeros_like(actualp)
                            # ---
                            for i in range(M):  # loop over X,Y & interpolates each axis separately
                                interp[:, i] = np.interp(
                                    ap_idx,             # actual points indices
                                    subs_idx,           # subsampled indices
                                    subsampled[:, i]    # actual values
                                )
                            interp = np.round(interp, decimals=2)
                            
                            # --- custom implementation
                            # diffs = subsampled[1:] - subsampled[:-1]
                            # diffs = np.vstack([diffs, np.array([0.,0.])])
                            # d_xy = diffs / step_size

                            # interp = np.zeros_like(actualp)
                            # interp[0::step_size] = subsampled  # place knowns (actual data)
                            # for step in range(1, step_size):
                            #     if interp[step-1::step_size].shape[0] != d_xy.shape[0]:
                            #         d_xy = d_xy[:-1]
                            #     interp_pts = interp[step-1::step_size] + d_xy  # missing 1 value; last point is missing, so pad it
                            #     if interp[step::step_size].shape[0] != interp_pts.shape[0]: # remove last diff
                            #         interp_pts = interp_pts[:-1]
                            #     interp[step::step_size] = interp_pts
                        
                            # compute deviation
                            err_dist = np.sqrt(np.sum((actualp - interp)**2, axis=1))  # euclidean distances
                            is_interp = np.ones(N, dtype=bool)
                            is_interp[subs_idx] = False  # mask to filter results
                            mean_err = np.mean(err_dist[is_interp])  # mean (avg. err) over dist
                            range_x = np.max(actualp[:, 0]) - np.min(actualp[:, 0])
                            range_y = np.max(actualp[:, 1]) - np.min(actualp[:, 1])
                            movement_scale = np.sqrt(range_x**2 + range_y**2)  # represents max possible dist, serves as a normalization factor
                            if movement_scale > 0:
                                dev.append((mean_err / movement_scale) * 100)
                            else:
                                dev.append(0.0)
                        
                        meta_dict["interp_err"] = np.array(dev).mean()
                        del df_players
                        del actualp
                        del subsampled
                        # ---- subsample orig. df
                        selected_timestamps = unique_timestamps[::step_size]
                        df = df[df[df.columns[0]].isin(selected_timestamps)]
                
                # reset timestamps to zero
                # df[df.columns[0]] = df[df.columns[0]].apply(lambda x: x - unique_timestamps.min())
                # df[df.columns[0]] = df[df.columns[0]] - unique_timestamps.min()     

                # map player and team ids
                # if not is_numeric_dtype(df["team_id"].dtype):
                unique_teams = df["team_id"].unique()
                
                if parameters["format"] == "kinexon":
                    ball_id = parameters["team_id_ball"]
                elif parameters["format"] == "dfl":
                    ball_id = 'BALL'
                    
                df["team_id"].replace(ball_id, 1)
                meta_dict["team_ids"].update({ 1 : ball_id})

                for i, team_label in enumerate(unique_teams, start=2):    
                    # df.loc[df["team_id"] == team_label, "team_id"] = i
                    if team_label != ball_id:
                        df["team_id"] = df["team_id"].replace(team_label, i)
                        meta_dict["team_ids"].update({ i : team_label})

                if not is_numeric_dtype(df["player_id"].dtype):
                    unique_players = df["player_id"].unique()
                    for i, player_label in enumerate(unique_players, start=1):
                        df["player_id"] = df["player_id"].replace(player_label, i)
                        meta_dict["player_ids"].update({ i : player_label})
                    
                # TODO: do this while XML parsing when implement etree iterparse
                if parameters["format"] == "dfl":
                    df["game_section"] = df["game_section"].replace("firstHalf", 1)
                    df["game_section"] = df["game_section"].replace("secondHalf", 2)
                
                # grouped_data = df.groupby(
                #     'timestamp', group_keys=False
                # ).apply(
                #     # lambda x: x.to_dict(orient='records'),
                #     # NOTE: numpy solution, faster but upcasts every value to float...
                #     # lambda x: x.to_numpy().tolist(),
                #     lambda x: [list(row) for row in x.itertuples(index=False)],
                #     include_groups=False
                # )
                # py_dict = grouped_data.to_dict()
                # for i, k in enumerate(list(py_dict.keys())):  # reindex grouped data to correct for 
                #     py_dict[corrected_series[i]] = py_dict.pop(k)
                
                grouped_data = {}
                for timestamp, group in df.groupby('timestamp', group_keys=False):
                    grouped_data[timestamp] = [list(row[1:]) for row in group.itertuples(index=False)]

                freq = (1000. / actual_fps)
                corrected_series = np.astype(
                    np.rint(np.arange(0.0, len(grouped_data)*freq, step=freq)), 
                    np.int64
                )
                # Create final dictionary with corrected keys
                py_dict = {corrected_series[i]: data for i, data in enumerate(grouped_data.values())}
                del grouped_data
                del df
                # -----------------
        # ----------------- OUTPUT
        with data_manager.create_data("PositionData") as pos_data:
            pos_data.name = "pos_data"
            pos_data.tracking_data_id = parameters.get('tracking_data_id')  # Required field
            pos_data.meta_data = json.dumps(meta_dict)
            pos_data.pos = json.dumps(py_dict)

            self.update_callbacks(callbacks, progress=1.0)
        
        return {"pos_data": pos_data}
        