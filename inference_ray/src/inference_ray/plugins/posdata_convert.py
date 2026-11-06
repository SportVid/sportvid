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
    "field_width": 68.,
    "team_id_ball": "ball",
    "team_id_ref": "",
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

        self.meta_dict = self._fresh_meta_dict()
        self.py_dict = {}

    @staticmethod
    def _fresh_meta_dict():
        return {
            "team_ids": {},
            "player_ids": {},
            "ref_ids": {},
            "ball_ids": {},
        }

    def parse_knx(self, t_data, parameters):
        import pandas as pd
        
        df = pd.read_csv(t_data, delimiter=parameters["delimiter"])
        
        # Rename relevant Kinexon columns to unified names
        df = df.rename(columns={
            "ts in ms": "timestamp", 
            "number": "player_id",
            "full name": "player_name",
            "group id": "team_id",
            "group name": "team_name",
            "x in m": "pos_x", 
            "y in m": "pos_y"
        })
        
        df["game_section"] = 0
        df["player_number"] = df["player_id"]  # For KNX, player_id IS the shirt number
        
        # Keep only relevant columns, drop everything else (speed, acceleration, etc.)
        keep_cols = ['timestamp', 'player_id', 'player_name', 'team_id', 'team_name', 'game_section', 'pos_x', 'pos_y', 'player_number']
        df = df[[c for c in keep_cols if c in df.columns]]
        
        df["pos_x"] = df["pos_x"].apply(lambda x: round(x, ndigits=2))
        df["pos_y"] = df["pos_y"].apply(lambda x: round(x, ndigits=2))

        # Tag entity kind via user-supplied team_name aliases (defaults: ball="ball", ref="").
        ball_alias = (parameters.get("team_id_ball") or "").strip().lower()
        ref_alias = (parameters.get("team_id_ref") or "").strip().lower()
        def _kind(tname):
            if not isinstance(tname, str):
                return "player"
            tn = tname.strip().lower()
            if ball_alias and tn == ball_alias:
                return "ball"
            if ref_alias and tn == ref_alias:
                return "ref"
            return "player"
        df["entity_kind"] = df["team_name"].apply(_kind)

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

        ref_name_lookup = {}
        for ref_el in root.findall("./MatchInformation/Referees/Referee"):
            pid = ref_el.get("PersonId")
            pname = ref_el.get("Shortname") or pid
            ref_name_lookup[pid] = pname

        # Map names and numbers into DataFrame
        df["team_name"] = df["team_id"].map(team_name_lookup)
        df["player_name"] = df["player_id"].map(player_name_lookup)
        df["player_number"] = df["player_id"].map(player_number_lookup)

        # Tag entity kind: ball (TeamId=='BALL'), ref (PersonId in referees), else player.
        ref_ids = set(ref_name_lookup.keys())
        df["entity_kind"] = "player"
        df.loc[df["team_id"] == "BALL", "entity_kind"] = "ball"
        df.loc[df["player_id"].isin(ref_ids), "entity_kind"] = "ref"
        # Refs lack a team_name (their FrameSet TeamId is typically empty); use shortname for display.
        ref_mask = df["entity_kind"] == "ref"
        df.loc[ref_mask, "player_name"] = df.loc[ref_mask, "player_id"].map(ref_name_lookup)

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
        
        # Reset instance state to prevent data leaking between calls
        self.meta_dict = self._fresh_meta_dict()
        self.py_dict = {}

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
        self.update_callbacks(callbacks, progress=0.25)  # raw tracking data parsed

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
                    player_number_map[pid] = int(pnum) if pd.notna(pnum) else None
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
            unique_timestamps = np.sort(df[df.columns[0]].unique())
            diffs = unique_timestamps[1:] - unique_timestamps[:-1]
            freq = np.median(diffs)  # compute median frame time to determine original fps, more robust to outliers than mean
            origin_fps = int(np.rint(1000./freq))
            logging.info(f"posdata_convert: freq={freq:.4f}ms, origin_fps={origin_fps}, requested_fps={parameters['fps']}")
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
                        lambda x: x[['pos_x', 'pos_y']].to_numpy(),  # type: ignore
                        include_groups=False
                    )
                    actualp, subsampled = None, None
                    _player_ids = list(df["player_id"].unique())
                    _n_players = max(len(_player_ids), 1)
                    for _p_idx, player_id in enumerate(_player_ids):
                        # resampling error estimation per player -- the main iterative
                        # cost of this plugin; map it into the 0.30..0.80 band.
                        self.update_callbacks(
                            callbacks, progress=0.30 + 0.50 * (_p_idx / _n_players)
                        )
                        actualp = np.array(df_players[player_id], dtype=np.float32)  # [[x,y]]
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

            if parameters["format"] == "dfl":
                self.meta_dict["kickoff_time"] = int(  # type: ignore
                    self.meta_dict["kickoff_time"] - unique_timestamps.min())

            _n = lambda v, f: v if pd.notna(v) else str(f)

            # entity_kind tagging is set in parse_knx/parse_dfl. Default everything to 'player' if missing.
            if 'entity_kind' not in df.columns:
                df['entity_kind'] = 'player'

            # ---- New team_id scheme: 0=ball, 2=refs, 3+=teams (sorted by player count desc)
            ball_orig = df.loc[df['entity_kind'] == 'ball', 'team_id'].unique().tolist()
            ref_orig = df.loc[df['entity_kind'] == 'ref', 'team_id'].unique().tolist()
            player_team_counts = (
                df.loc[df['entity_kind'] == 'player']
                .groupby('team_id', observed=True)['player_id'].nunique()
                .sort_values(ascending=False)
            )
            teams_sorted = player_team_counts.index.tolist()

            team_id_mapping = {}
            for tid in ball_orig:
                team_id_mapping[tid] = 0
            if ball_orig:
                self.meta_dict["team_ids"][0] = {"id": ball_orig[0], "name": "Ball"}
            for tid in ref_orig:
                team_id_mapping[tid] = 2
            if ref_orig:
                self.meta_dict["team_ids"][2] = {
                    "id": ref_orig[0] if ref_orig[0] else "_refs",
                    "name": "Referees",
                }
            for new_tid, orig_tid in enumerate(teams_sorted, start=3):
                team_id_mapping[orig_tid] = new_tid
                self.meta_dict["team_ids"][new_tid] = {
                    "id": orig_tid,
                    "name": _n(team_name_map.get(orig_tid), orig_tid),
                }
            df["team_id"] = df["team_id"].map(team_id_mapping).astype('int16')

            # ---- Per-kind entity_id mapping (each kind gets its own 1..N namespace).
            # Frame data carries (entity_id, team_id); team_id (0=ball, 2=ref, ≥3=player) selects which dict to look up.
            kind_to_dict = {'player': "player_ids", 'ref': "ref_ids", 'ball': "ball_ids"}
            full_pid_map = {}
            for kind, dict_key in kind_to_dict.items():
                mask = df['entity_kind'] == kind
                if not mask.any():
                    continue
                origs = df.loc[mask, 'player_id'].unique()
                kind_map = {orig: new_id for new_id, orig in enumerate(origs, start=1)}
                full_pid_map.update(kind_map)
                for orig_pid, new_id in kind_map.items():
                    new_team_id = int(df.loc[mask & (df['player_id'] == orig_pid), 'team_id'].iloc[0])
                    entry = {"id": orig_pid}
                    if kind == 'player':
                        entry["name"] = _n(player_name_map.get(orig_pid), orig_pid)
                        entry["number"] = player_number_map.get(orig_pid, orig_pid)
                        entry["team_id"] = new_team_id
                    elif kind == 'ref':
                        entry["name"] = _n(player_name_map.get(orig_pid), orig_pid)
                    self.meta_dict[dict_key][new_id] = entry
            df["player_id"] = df["player_id"].map(full_pid_map).astype('int16')

            # entity_kind is no longer needed in the per-frame payload (kind is derivable from team_id).
            df = df.drop('entity_kind', axis=1)

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
            self.update_callbacks(callbacks, progress=0.85)
            df = df.dropna(subset=['pos_x', 'pos_y'])
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