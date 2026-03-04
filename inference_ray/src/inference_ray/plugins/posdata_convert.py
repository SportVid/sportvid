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

"""
Conversion returns a JSON with player data sorted by timestamp.
JSON is native to JavaScript and should be faster than any tensorial or numPy NDarray representation,
which again would require some special libraries to interpret/parse them in the frontend.

# TODO: Maybe stream data chunk by chunk? In general, this would be useful especially when we run into data transfer/memory overhead issues.
JSON responses can get quite large, already reduced redundancy by introducing a meta dict and a more compact list-based representation.
Could use floodlight import and scavenge the results.
Compression algorithms (frontend decoder)? 
"""
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
        
        from collections import defaultdict
        self.meta_dict = defaultdict(team_ids={}, player_ids={})
        self.py_dict = {}

    def parse_knx(self, t_data, parameters):
        import pandas as pd
        
        df = pd.read_csv(t_data, delimiter=parameters["delimiter"])
         
        df = df.drop(['formatted local time', 'mapped id'], axis=1)
        df["game_section"] = 0
        df = df.rename(columns={
            "ts in ms": "timestamp", 
            "number": "player_id",
            "full name": "player_name",
            "group id": "team_id",
            "group name": "team_name",
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
        
        # For KNX, player_id IS the shirt number
        df["player_number"] = df["player_id"]
        
        return df, parameters["field_length"], parameters["field_width"]
        
    def parse_dfl(self, t_data, m_data):
        import pandas as pd
        
        from datetime import datetime
        from io import StringIO
        from lxml import etree

        # --- old parsing
        # DFL_XSL = """
        # <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
        #     <xsl:output method="xml" omit-xml-declaration="no" indent="yes"/>
        #     <xsl:strip-space elements="*"/>
        #     <xsl:template match="/PutDataRequest">
        #         <xsl:copy>
        #             <xsl:apply-templates select="//Positions"/>
        #         </xsl:copy>
        #     </xsl:template>
        #     <xsl:template match="Frame">
        #         <record>
        #             <timestamp><xsl:value-of select="@T"/></timestamp>
        #             <player_id><xsl:value-of select="../@PersonId"/></player_id>
        #             <team_id><xsl:value-of select="../@TeamId"/></team_id>
        #             <game_section><xsl:value-of select="../@GameSection"/></game_section>
        #             <pos_x><xsl:value-of select="@X"/></pos_x>
        #             <pos_y><xsl:value-of select="@Y"/></pos_y>
        #         </record>
        #     </xsl:template>
        # </xsl:stylesheet>
        # """

        # df = pd.read_xml(
        #     t_data,
        #     stylesheet=StringIO(DFL_XSL),
        #     xpath='//record'
        # )
        # df[df.columns[0]] = df[df.columns[0]].apply(lambda x: int(datetime.fromisoformat(x).timestamp()*1000))
        # df["game_section"] = df["game_section"].replace("firstHalf", 1)
        # df["game_section"] = df["game_section"].replace("secondHalf", 2)
        
        # --- new parsing
        data_records = []
        for _, frame_set in etree.iterparse(t_data, tag="FrameSet"):
            frames = frame_set.findall("Frame")
            # frames = [frame for frame in frame_set.iterfind("Frame")]
            
            player_id = frame_set.get("PersonId")
            team_id = frame_set.get("TeamId")
            game_section = 1 if frame_set.get("GameSection") == 'firstHalf' else 2
            records = [
                {
                    'timestamp': int(datetime.fromisoformat(frame.get("T")).timestamp() * 1000),
                    'player_id': player_id,
                    'team_id': team_id,
                    'game_section': game_section,
                    'pos_x': float(frame.get("X")),
                    'pos_y': float(frame.get("Y"))
                }
                for frame in frames
            ]
            data_records.extend(records)
            
            frame_set.clear()
            # clear parent references to prevent memory leaks
            for ancestor in frame_set.xpath('ancestor-or-self::*'):
                while ancestor.getprevious() is not None:
                    del ancestor.getparent()[0]
    
        # Create DataFrame from records
        df = pd.DataFrame.from_records(data_records)
        del data_records
        
        tree = etree.parse(m_data)
        root = tree.getroot()

        pitch_x = float(root.findall("./MatchInformation/Environment")[0].attrib["PitchX"])
        pitch_y = float(root.findall("./MatchInformation/Environment")[0].attrib["PitchY"])
        
        # ---- Extract team and player names/numbers from matchinfo XML
        team_name_lookup = {}
        player_name_lookup = {}
        player_number_lookup = {}
        for team_el in root.findall("./MatchInformation/Teams/Team"):
            tid = team_el.get("TeamId")
            tname = team_el.get("TeamName") or tid
            team_name_lookup[tid] = tname
            for player_el in team_el.findall("Players/Player"):
                pid = player_el.get("PersonId")
                pname = player_el.get("Shortname") or pid
                pnumber = player_el.get("ShirtNumber", "")
                player_name_lookup[pid] = pname
                player_number_lookup[pid] = int(pnumber) if pnumber.isdigit() else pname
        
        # Map names and numbers into DataFrame
        df["team_name"] = df["team_id"].map(team_name_lookup)
        df["player_name"] = df["player_id"].map(player_name_lookup)
        df["player_number"] = df["player_id"].map(player_number_lookup)

        self.meta_dict.update({
            "kickoff_time": int(datetime.fromisoformat(root.findall("./MatchInformation/General")[0].attrib["KickoffTime"]).timestamp()*1000),
            "total_time_first_half": root.findall("./MatchInformation/OtherGameInformation")[0].attrib["TotalTimeFirstHalf"],
            "total_time_second_half": root.findall("./MatchInformation/OtherGameInformation")[0].attrib["TotalTimeSecondHalf"],
            "playing_time_first_half": root.findall("./MatchInformation/OtherGameInformation")[0].attrib["PlayingTimeFirstHalf"],
            "playing_time_second_half": root.findall("./MatchInformation/OtherGameInformation")[0].attrib["PlayingTimeSecondHalf"]
        }) # type: ignore
        
        return df, pitch_x, pitch_y

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
        from pandas.api.types import is_numeric_dtype
        
        if "format" not in parameters:
            raise ValueError("'format' is required for plugin execution.")
        
        with inputs["tracking_data"] as input_data:
            with input_data.open_file() as t_data:
                try:
                # ----------------- PARSE
                    if parameters["format"] == "kinexon":
                        df, PITCH_SIZE_X, PITCH_SIZE_Y = self.parse_knx(t_data, parameters)
                    elif parameters["format"] == "dfl":
                        with inputs["meta_data"] as meta_data:
                            with meta_data.open_file() as m_data:
                                df, PITCH_SIZE_X, PITCH_SIZE_Y = self.parse_dfl(t_data, m_data)
                    else:
                        df = pd.DataFrame()
                except Exception as e:
                    df = pd.DataFrame()
                    logging.error(f"Failed to parse tracking data due to an exception: {e}", exc_info=True)
                # -----------------
        def post_process_df(df):
            # ----------------- POST PROCESS
            # optimize dtypes
            df = df.astype({
                'player_id': 'category',
                'team_id': 'category',
                'game_section': 'int8',
                'pos_x': 'float32',
                'pos_y': 'float32'
            })
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]  # remove empty columns
            # ---- Extract name/number mappings and drop auxiliary columns
            player_name_map = {}
            player_number_map = {}
            team_name_map = {}
            if 'player_name' in df.columns:
                for pid, pname in df[['player_id', 'player_name']].drop_duplicates().values:
                    player_name_map[pid] = pname
                df = df.drop('player_name', axis=1)
            if 'player_number' in df.columns:
                for pid, pnum in df[['player_id', 'player_number']].drop_duplicates().values:
                    player_number_map[pid] = pnum
                df = df.drop('player_number', axis=1)
            if 'team_name' in df.columns:
                for tid, tname in df[['team_id', 'team_name']].drop_duplicates().values:
                    team_name_map[tid] = tname
                df = df.drop('team_name', axis=1)
            # ---- Data/Coords normalization
            # origin (0,0)^T is at the kickoff, i.e. x values left of kickoff are negative & y values below kickoff are negative
            if parameters["origin"] == "kickoff":  
                MAX_X = PITCH_SIZE_X / 2.0
                MAX_Y = PITCH_SIZE_Y / 2.0
                df["pos_x"] = (df["pos_x"] + MAX_X) / PITCH_SIZE_X
                df["pos_y"] = 1.0 - ((df["pos_y"] + MAX_Y) / PITCH_SIZE_Y)  # correct for inverted Y-axis
            # origin (0,0)^T is at the bottom left, i.e. all values on both axes are >= 0
            elif parameters["origin"] == "bottom_left":
                MAX_X = PITCH_SIZE_X
                MAX_Y = PITCH_SIZE_Y
                df["pos_x"] = df["pos_x"] / PITCH_SIZE_X  # normalize to a range of [0,1]
                df["pos_y"] = (MAX_Y - df["pos_y"]) / PITCH_SIZE_Y  # inverted Y-axis, images start at top left corner
        
            # ---- FPS filtering: checks if specified fps parameter is in an applicable range
            unique_timestamps = df[df.columns[0]].unique()  # all unique timestamps, in order of appearance
            diffs = unique_timestamps[1:] - unique_timestamps[:-1]
            freq = np.median(diffs)
            origin_fps = int(np.rint(1000./freq))
            actual_fps = origin_fps
            
            step_size = 0
            if parameters["fps"] > 0 and (parameters["fps"] != origin_fps):
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
                    self.meta_dict["fps"] = actual_fps # type: ignore
                    
                    step_size = np.int8(origin_fps/actual_fps)  # compute step size for filtering
                    # ---- calc err. of linear interpolation
                    dev = list()
                    df_players = df.groupby(
                        'player_id', group_keys=False
                    ).apply(
                        lambda x: x.to_numpy(),  # type: ignore
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
                    
                    self.meta_dict["interp_err"] = np.array(dev).mean()
                    del df_players
                    del actualp
                    del subsampled
                    # ---- subsample orig. df
                    selected_timestamps = unique_timestamps[::step_size]
                    df = df[df[df.columns[0]].isin(selected_timestamps)]

            unique_teams = list(df["team_id"].unique())
            if parameters["format"] == "kinexon":
                ball_name = parameters["team_id_ball"]
                # reverse lookup: find team_id whose team_name matches the ball parameter
                ball_id = next((tid for tid, tname in team_name_map.items() if tname == ball_name), ball_name)
            elif parameters["format"] == "dfl":
                ball_id = 'BALL'
                self.meta_dict["kickoff_time"] = int( # type: ignore
                    self.meta_dict["kickoff_time"] - unique_timestamps.min()) 
            
            # ---- map team ids (build full mapping first, then apply at once to avoid category collisions)
            team_id_mapping = {ball_id: 1}
            self.meta_dict["team_ids"].update({ 1 : {"id": ball_id, "name": team_name_map.get(ball_id) or str(ball_id)}})
            next_id = 2
            for team_label in unique_teams:
                if team_label == ball_id:
                    continue
                team_id_mapping[team_label] = next_id
                self.meta_dict["team_ids"].update({ next_id : {"id": team_label, "name": team_name_map.get(team_label) or str(team_label)}})
                next_id += 1
            df["team_id"] = df["team_id"].map(team_id_mapping).astype('category')
            
            # ---- map player ids
            unique_players = df["player_id"].unique()
            player_id_mapping = {}
            for i, player_label in enumerate(unique_players, start=1):
                player_id_mapping[player_label] = i
                self.meta_dict["player_ids"].update({ i : {
                    "id": player_label,
                    "name": player_name_map.get(player_label) or str(player_label),
                    "number": player_number_map.get(player_label, player_label)
                }})
            df["player_id"] = df["player_id"].map(player_id_mapping).astype('category')

            # --- old dict conversion
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
            
            # --- new dict conversion
            grouped_data = {}
            for timestamp, group in df.groupby('timestamp', group_keys=False):
                grouped_data[timestamp] = [list(row[1:]) for row in group.itertuples(index=False)]
            freq = (1000. / actual_fps)
            corrected_series = np.rint(np.arange(0.0, len(grouped_data)*freq, step=freq)).astype(np.int32)
            self.py_dict = {corrected_series[i].item(): data for i, data in enumerate(grouped_data.values())}
            del grouped_data
            del df
        
        if not df.empty: post_process_df(df)
        
        # ----------------- OUTPUT
        class NPEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super(NPEncoder, self).default(obj)


        with data_manager.create_data("PositionData") as pos_data:
            pos_data.name = "pos_data"
            pos_data.tracking_data_id = parameters.get('tracking_data_id')  # Required field
            pos_data.meta_data = json.dumps(self.meta_dict, cls=NPEncoder)
            pos_data.pos = json.dumps(self.py_dict, cls=NPEncoder)

            self.update_callbacks(callbacks, progress=1.0)
        
        return {"pos_data": pos_data}
        