import logging
import os
import tempfile

import pandas as pd
from typing import Callable, Dict

from data import KpiData, TrackingData, PositionData
from data import DataManager, Data

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {
    "delimiter": ";",
    "field_length": 105.0,
    "field_width": 68.0,
    "origin": "kickoff",
}

requires = {
    "tracking_data": TrackingData,  # used for kinexon/dfl formats
    # "pos_data": PositionData,     # used for sportvid format (optional, not enforced)
}

provides = {
    "kpi_data": KpiData,
}


@AnalyserPluginManager.export("kpi_computation")
class KpiComputation(
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
        import json
        import numpy as np

        import floodlight.io.kinexon as knx
        import floodlight.io.dfl as dfl
        from floodlight.transforms.filter import butterworth_lowpass, savgol_lowpass
        from floodlight.models.kinematics import DistanceModel, VelocityModel
        from floodlight.models.kinetics import MetabolicPowerModel
        from floodlight.models.geometry import CentroidModel

        if "format" not in parameters:
            raise ValueError("'format' is required for plugin execution.")

        fmt = parameters["format"]

        # Load filter parameters if provided
        filter_type = parameters.get("filter_type")  # "butterworth_lowpass", "savgol_lowpass", or None
        filter_kwargs = {}
        if filter_type == "butterworth_lowpass":
                filter_kwargs["order"] = int(parameters.get("order", 3))
                filter_kwargs["Wn"] = float(parameters.get("Wn", 1))
        elif filter_type == "savgol_lowpass":
                filter_kwargs["window_length"] = int(parameters.get("window_length", 5))
                filter_kwargs["poly_order"] = int(parameters.get("poly_order", 3))
        
        # Load posdata metadata if available
        pos_meta_raw = parameters.get("pos_meta", "")
        pos_meta = json.loads(pos_meta_raw) if pos_meta_raw else None

        # Build reverse lookups from posdata metadata.
        # New schema: ref_ids and ball_ids are top-level dicts; player_ids contains only players.
        team_id_by_orig = {}   # original_id → posdata int_id
        player_id_by_orig = {}  # original_id → posdata int_id (players only)

        if pos_meta:
            for int_id_str, info in pos_meta.get("team_ids", {}).items():
                team_id_by_orig[info["id"]] = int(int_id_str)
            for int_id_str, info in pos_meta.get("player_ids", {}).items():
                player_id_by_orig[info["id"]] = int(int_id_str)

        # Skip teams that aren't real player teams: 1=ball, 2=refs, 0=inactive.
        # `ball_team_ids` is kept (set of original team ids) but populated for both ball AND ref groups,
        # since both must be filtered out of KPI computation.
        SKIP_TEAM_IDS = {0, 1, 2}
        ball_team_ids = set()
        framerate = None

        if fmt not in ("kinexon", "dfl", "sportvid"):
            raise ValueError(f"Unsupported format: '{fmt}'. Use 'dfl', 'kinexon', or 'sportvid'.")

        # ----------------- PARSING (kinexon / dfl)
        if fmt in ("kinexon", "dfl"):
            with inputs["tracking_data"] as input_data:
                with input_data.open_file() as t_data:
                    if fmt == "kinexon":
                        raw_bytes = t_data.read()
                        if raw_bytes.startswith(b'\xef\xbb\xbf'):
                            raw_bytes = raw_bytes[3:]
                        delim = parameters.get("delimiter", ";").encode()
                        header_end = raw_bytes.find(b'\n')
                        if header_end != -1:
                            header_bytes = raw_bytes[:header_end].rstrip(b'\r')
                            body_bytes = raw_bytes[header_end:]
                            cols = [c.strip() for c in header_bytes.split(delim)]
                            cols.append(b'_dummy')
                            raw_bytes = delim.join(cols) + b'\n' + body_bytes.lstrip(b'\n')
                        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as tmp:
                            tmp.write(raw_bytes)
                            tmp_path = tmp.name
                        try:
                            # NOTE: knx reader returns lists for pos_data and teamsheets (different from DFL reader below, returning same-named variables as dicts)
                            pos_data = knx.read_position_data_csv(tmp_path, delimiter=parameters.get("delimiter", ";")) # pos_data is List[XY]
                            teamsheets = knx.read_teamsheets_from_csv(tmp_path, delimiter=parameters.get("delimiter", ";")) # teamsheets is List[Teamsheet]
                            csv_data = pd.read_csv(tmp_path, delimiter=parameters.get("delimiter", ";"))
                            group_id_map = csv_data[["number", "group id"]].drop_duplicates(subset=["number"])
                            for idx, i in enumerate(teamsheets):
                                teamsheets[idx].teamsheet = pd.merge(
                                    i.teamsheet.astype({"number": int}),
                                    group_id_map,
                                    on=["number"]
                                )
                        finally:
                            os.unlink(tmp_path)

                        for idx, ts in enumerate(teamsheets):
                            df = ts.teamsheet.copy()
                            group_id_val = df['group id'].iloc[0] if not ts.teamsheet.empty else f"team_{idx+1}"
                            tid = team_id_by_orig.get(group_id_val, group_id_val)
                            if pos_meta:
                                if tid in SKIP_TEAM_IDS:
                                    ball_team_ids.add(group_id_val)
                                    continue
                            elif "ball" in str(group_id_val).lower():
                                ball_team_ids.add(group_id_val)
                                continue

                            df['pid'] = df['number'].map(player_id_by_orig) if pos_meta else df['number'].astype(str)
                            df['tid'] = tid
                            teamsheets[idx].teamsheet = df

                        if pos_data:
                            framerate = int(pos_data[0].framerate) if pos_data[0].framerate else 25

                    elif fmt == "dfl":
                        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.xml', delete=False) as tmp_data:
                            tmp_data.write(t_data.read())
                            tmp_data_path = tmp_data.name
                        try:
                            with inputs["meta_data"] as meta_input:
                                with meta_input.open_file() as m_data:
                                    with tempfile.NamedTemporaryFile(mode='w+b', suffix='.xml', delete=False) as tmp_meta:
                                        tmp_meta.write(m_data.read())
                                        tmp_meta_path = tmp_meta.name
                                    try:
                                        # NOTE: DFL reader returns dicts for pos_data and teamsheets (different from knx reader above, returning same-named variables as lists)
                                        pos_data, _, _, teamsheets, _ = dfl.read_position_data_xml(tmp_data_path, tmp_meta_path) # pos_data is Dict[half_name, Dict[team_name, XY]] and teamsheets is Dict[team_name, Teamsheet]
                                    finally:
                                        os.unlink(tmp_meta_path)
                        finally:
                            os.unlink(tmp_data_path)

                        for team_name, team_ts in teamsheets.items():
                            df = team_ts.teamsheet.copy()
                            group_id_val = df['tID'].iloc[0] if not team_ts.teamsheet.empty else f"team_{team_name}"
                            tid = team_id_by_orig.get(group_id_val, group_id_val)

                            if pos_meta:
                                if tid in SKIP_TEAM_IDS:
                                    ball_team_ids.add(group_id_val)
                                    continue

                            df["pid"] = df["pID"].map(player_id_by_orig) if pos_meta else df["pID"].astype(str)
                            df["tid"] = tid
                            teamsheets[team_name].teamsheet = df

                        first_xy = next(iter(next(iter(pos_data.values())).values()))
                        framerate = int(first_xy.framerate) if first_xy.framerate else 25

        # ----------------- PARSE sportvid (PositionData input, no TrackingData)
        if fmt == "sportvid":
            from floodlight.core.xy import XY
            from floodlight.core.teamsheet import Teamsheet
            from collections import defaultdict as _defaultdict

            with inputs["pos_data"] as input_data:
                sportvid_meta = json.loads(input_data.meta_data)
                pos_json = json.loads(input_data.pos)

            framerate = int(sportvid_meta.get("fps", 25))
            field_length = float(parameters.get("field_length", 105.0))
            field_width = float(parameters.get("field_width", 68.0))
            origin = parameters.get("origin", "kickoff")

            # sorted frame timestamps (ms, ascending)
            sorted_ts_keys = sorted(pos_json.keys(), key=lambda k: int(k))
            n_frames_sportvid = len(sorted_ts_keys)

            # Build player → team mapping. Skip non-player entities (ball=1, refs=2, inactive=0).
            player_team_map = {}
            for ts_key in sorted_ts_keys:
                for row in pos_json[ts_key]:
                    pid, tid = int(row[0]), int(row[1])
                    if tid not in SKIP_TEAM_IDS and pid not in player_team_map:
                        player_team_map[pid] = tid

            # Group players by team, each group sorted for deterministic column order
            teams_players = _defaultdict(list)
            for pid, tid in sorted(player_team_map.items()):
                teams_players[tid].append(pid)
            for tid in teams_players:
                teams_players[tid].sort()

            # Build XY array and Teamsheet per team
            sportvid_pos_data = {}    # team_id_int → XY
            sportvid_teamsheets = {}  # team_id_int → Teamsheet

            for tid, players in teams_players.items():
                n_players = len(players)
                player_col_idx = {pid: i for i, pid in enumerate(players)}
                xy_arr = np.full((n_frames_sportvid, 2 * n_players), np.nan)

                for fi, ts_key in enumerate(sorted_ts_keys):
                    for row in pos_json[ts_key]:
                        p_id, t_id = int(row[0]), int(row[1])
                        if t_id != tid:
                            continue
                        pos_x_norm = float(row[3])
                        pos_y_norm = float(row[4])
                        # Denormalize [0,1] back to meters
                        if origin == "kickoff":
                            x_m = pos_x_norm * field_length - field_length / 2.0
                            y_m = (1.0 - pos_y_norm) * field_width - field_width / 2.0
                        elif origin == "bottom_left":
                            x_m = pos_x_norm * field_length
                            y_m = (1.0 - pos_y_norm) * field_width
                        else:
                            x_m = pos_x_norm * field_length - field_length / 2.0
                            y_m = (1.0 - pos_y_norm) * field_width - field_width / 2.0

                        col = player_col_idx[p_id]
                        xy_arr[fi, 2 * col] = x_m
                        xy_arr[fi, 2 * col + 1] = y_m

                sportvid_pos_data[tid] = XY(xy=xy_arr, framerate=framerate)

                player_ids_meta = sportvid_meta.get("player_ids", {})
                ts_rows = []
                for xi, pid in enumerate(players):
                    p_info = player_ids_meta.get(str(pid), {})
                    ts_rows.append({
                        "xID": xi,
                        "pID": str(pid),
                        "tID": str(tid),
                        "player": p_info.get("name", str(pid)),
                        "number": p_info.get("number", pid),
                        "pid": pid,
                        "tid": tid,
                    })
                sportvid_teamsheets[tid] = Teamsheet(teamsheet=pd.DataFrame(ts_rows))

            # expose pos_meta so the output section can reuse existing logic
            pos_meta = sportvid_meta

        # ----------------- COMPUTE KPIs
        all_frame_kpis = {}  # {absolute_frame_idx: [[player_id, dist, vel, metpow], ...]}
        frame_offset = 0


        if fmt == "kinexon":
            # pos_data is List[XY], one entry per group/team (including ball if tracked).
            team_kpi_arrays = {}  # i → (df_ts_sorted, dist_arr, vel_arr, metpow_arr)
            n_frames = None  

            for i, xy_obj in enumerate(pos_data):
                df_ts = teamsheets[i].teamsheet
                gid = df_ts['group id'].iloc[0]
                if gid in ball_team_ids:
                    continue

                # Apply filter, if enabled
                xy_filtered = xy_obj
                if filter_type == "butterworth_lowpass":
                    xy_filtered = butterworth_lowpass(xy_filtered, **filter_kwargs)
                elif filter_type == "savgol_lowpass":
                    xy_filtered = savgol_lowpass(xy_filtered, **filter_kwargs)

                dist_mod = DistanceModel()
                vel_mod = VelocityModel()
                metpow_mod = MetabolicPowerModel()
                cent_mod = CentroidModel()

                dist_mod.fit(xy_filtered)
                vel_mod.fit(xy_filtered)
                metpow_mod.fit(xy_filtered)
                cent_mod.fit(xy_filtered)

                dist_arr = np.array(dist_mod.distance_covered()).round(2)  # (T, N)
                dist_cumulative_arr = np.array(dist_mod.cumulative_distance_covered()).round(2)  # (T, N)
                vel_arr = np.array(vel_mod.velocity()).round(2)                       # (T, N)
                metpow_arr = np.array(metpow_mod.metabolic_power()).round(2)          # (T, N)
                metpow_cumulative_arr = np.array(metpow_mod.cumulative_metabolic_power()).round(2)  # (T, N)
                equiv_dist_arr = np.array(metpow_mod.equivalent_distance()).round(2)          # (T, N)
                equiv_dist_cumulative_arr = np.array(metpow_mod.cumulative_equivalent_distance()).round(2)  # (T, N)
                cent_dist_arr = np.array(cent_mod.centroid_distance(xy_filtered)).round(2)          # (T, N)

                team_kpi_arrays[i] = (df_ts.sort_values("xID").reset_index(drop=True), dist_arr, dist_cumulative_arr, vel_arr, metpow_arr, metpow_cumulative_arr, equiv_dist_arr, equiv_dist_cumulative_arr, cent_dist_arr)
                if n_frames is None:
                    n_frames = dist_arr.shape[0]

            if n_frames is not None:
                for i, (df_sorted, dist_arr, dist_cumulative_arr, vel_arr, metpow_arr, metpow_cumulative_arr, equiv_dist_arr, equiv_dist_cumulative_arr, cent_dist_arr) in team_kpi_arrays.items():
                    n_players = dist_arr.shape[1]

                    dist_list = dist_arr.tolist()
                    dist_cumulative_list = dist_cumulative_arr.tolist()
                    vel_list = vel_arr.tolist()
                    metpow_list = metpow_arr.tolist()
                    metpow_cumulative_list = metpow_cumulative_arr.tolist()
                    equiv_dist_list = equiv_dist_arr.tolist()
                    equiv_dist_cumulative_list = equiv_dist_cumulative_arr.tolist()
                    cent_dist_list = cent_dist_arr.tolist()

                    for frame_idx in range(n_frames):
                        if frame_idx not in all_frame_kpis:
                            all_frame_kpis[frame_idx] = []
                        for p in range(n_players):
                            row = df_sorted.iloc[p] if p < len(df_sorted) else None
                            pid = int(row['pid']) if row is not None and pd.notna(row['pid']) else -1
                            tid = int(row['tid']) if row is not None and pd.notna(row['tid']) else -1
                            d = dist_list[frame_idx][p]
                            d_cum = dist_cumulative_list[frame_idx][p]
                            v = vel_list[frame_idx][p]
                            m = metpow_list[frame_idx][p]
                            m_cum = metpow_cumulative_list[frame_idx][p]
                            e_dist = equiv_dist_list[frame_idx][p]
                            e_dist_cum = equiv_dist_cumulative_list[frame_idx][p]
                            c_dist = cent_dist_list[frame_idx][p]
                            all_frame_kpis[frame_idx].append([
                                pid,
                                tid,
                                None if d != d else d,
                                None if d_cum != d_cum else d_cum,
                                None if v != v else v,
                                None if m != m else m,
                                None if m_cum != m_cum else m_cum,
                                None if e_dist != e_dist else e_dist,
                                None if e_dist_cum != e_dist_cum else e_dist_cum,
                                None if c_dist != c_dist else c_dist,
                            ])


        elif fmt == "sportvid":
            # pos_data is Dict[team_id_int → XY], flat (no halves).
            team_kpi_arrays = {}
            n_frames = None

            for tid, xy_obj in sportvid_pos_data.items():
                xy_filtered = xy_obj
                if filter_type == "butterworth_lowpass":
                    xy_filtered = butterworth_lowpass(xy_filtered, **filter_kwargs)
                elif filter_type == "savgol_lowpass":
                    xy_filtered = savgol_lowpass(xy_filtered, **filter_kwargs)

                dist_mod = DistanceModel()
                vel_mod = VelocityModel()
                metpow_mod = MetabolicPowerModel()
                cent_mod = CentroidModel()

                dist_mod.fit(xy_filtered)
                vel_mod.fit(xy_filtered)
                metpow_mod.fit(xy_filtered)
                cent_mod.fit(xy_filtered)

                dist_arr = np.array(dist_mod.distance_covered()).round(2)
                dist_cumulative_arr = np.array(dist_mod.cumulative_distance_covered()).round(2)
                vel_arr = np.array(vel_mod.velocity()).round(2)
                metpow_arr = np.array(metpow_mod.metabolic_power()).round(2)
                metpow_cumulative_arr = np.array(metpow_mod.cumulative_metabolic_power()).round(2)
                equiv_dist_arr = np.array(metpow_mod.equivalent_distance()).round(2)
                equiv_dist_cumulative_arr = np.array(metpow_mod.cumulative_equivalent_distance()).round(2)
                cent_dist_arr = np.array(cent_mod.centroid_distance(xy_filtered)).round(2)

                df_ts = sportvid_teamsheets[tid].teamsheet.sort_values("xID").reset_index(drop=True)
                team_kpi_arrays[tid] = (df_ts, dist_arr, dist_cumulative_arr, vel_arr, metpow_arr, metpow_cumulative_arr, equiv_dist_arr, equiv_dist_cumulative_arr, cent_dist_arr)
                if n_frames is None:
                    n_frames = dist_arr.shape[0]

            if n_frames is not None:
                for tid, (df_sorted, dist_arr, dist_cumulative_arr, vel_arr, metpow_arr, metpow_cumulative_arr, equiv_dist_arr, equiv_dist_cumulative_arr, cent_dist_arr) in team_kpi_arrays.items():
                    n_players = dist_arr.shape[1]

                    dist_list = dist_arr.tolist()
                    dist_cumulative_list = dist_cumulative_arr.tolist()
                    vel_list = vel_arr.tolist()
                    metpow_list = metpow_arr.tolist()
                    metpow_cumulative_list = metpow_cumulative_arr.tolist()
                    equiv_dist_list = equiv_dist_arr.tolist()
                    equiv_dist_cumulative_list = equiv_dist_cumulative_arr.tolist()
                    cent_dist_list = cent_dist_arr.tolist()

                    for frame_idx in range(n_frames):
                        if frame_idx not in all_frame_kpis:
                            all_frame_kpis[frame_idx] = []
                        for p in range(n_players):
                            row = df_sorted.iloc[p] if p < len(df_sorted) else None
                            pid = int(row['pid']) if row is not None and pd.notna(row['pid']) else -1
                            t_id = int(row['tid']) if row is not None and pd.notna(row['tid']) else -1
                            d = dist_list[frame_idx][p]
                            d_cum = dist_cumulative_list[frame_idx][p]
                            v = vel_list[frame_idx][p]
                            m = metpow_list[frame_idx][p]
                            m_cum = metpow_cumulative_list[frame_idx][p]
                            e_dist = equiv_dist_list[frame_idx][p]
                            e_dist_cum = equiv_dist_cumulative_list[frame_idx][p]
                            c_dist = cent_dist_list[frame_idx][p]
                            all_frame_kpis[frame_idx].append([
                                pid,
                                t_id,
                                None if d != d else d,
                                None if d_cum != d_cum else d_cum,
                                None if v != v else v,
                                None if m != m else m,
                                None if m_cum != m_cum else m_cum,
                                None if e_dist != e_dist else e_dist,
                                None if e_dist_cum != e_dist_cum else e_dist_cum,
                                None if c_dist != c_dist else c_dist,
                            ])

        elif fmt == "dfl":
            # pos_data is Dict[half_name → Dict[team_name → XY]].
            # Halves are concatenated into a flat frame index using frame_offset.
            # Ball is included as a regular group; its player_id falls back to "Ball_p0"
            # since it has no teamsheet entry.
            for half_name, teams_dict in pos_data.items():
                team_kpi_arrays = {}
                n_frames = None

                for team_name, xy_obj in teams_dict.items():
                    if team_name not in teamsheets:
                        continue
                    df_ts = teamsheets[team_name].teamsheet
                    if df_ts['tID'].iloc[0] in ball_team_ids:
                        continue

                    # Apply filter, if enabled
                    xy_filtered = xy_obj
                    if filter_type == "butterworth_lowpass":
                        xy_filtered = butterworth_lowpass(xy_filtered, **filter_kwargs)
                    elif filter_type == "savgol_lowpass":
                        xy_filtered = savgol_lowpass(xy_filtered, **filter_kwargs)

                    dist_mod = DistanceModel()
                    vel_mod = VelocityModel()
                    metpow_mod = MetabolicPowerModel()
                    cent_mod = CentroidModel()

                    dist_mod.fit(xy_filtered)
                    vel_mod.fit(xy_filtered)
                    metpow_mod.fit(xy_filtered)
                    cent_mod.fit(xy_filtered)

                    dist_arr = np.array(dist_mod.distance_covered()).round(2)  # (T, N)
                    dist_cumulative_arr = np.array(dist_mod.cumulative_distance_covered()).round(2)  # (T, N)
                    vel_arr = np.array(vel_mod.velocity()).round(2)                       # (T, N)
                    metpow_arr = np.array(metpow_mod.metabolic_power()).round(2)          # (T, N)
                    metpow_cumulative_arr = np.array(metpow_mod.cumulative_metabolic_power()).round(2)  # (T, N)
                    equiv_dist_arr = np.array(metpow_mod.equivalent_distance()).round(2)          # (T, N)
                    equiv_dist_cumulative_arr = np.array(metpow_mod.cumulative_equivalent_distance()).round(2)  # (T, N)
                    cent_dist_arr = np.array(cent_mod.centroid_distance(xy_filtered)).round(2)          # (T, N)
                    
                    team_kpi_arrays[team_name] = (dist_arr, dist_cumulative_arr, vel_arr, metpow_arr, metpow_cumulative_arr, equiv_dist_arr, equiv_dist_cumulative_arr, cent_dist_arr)
                    if n_frames is None:
                        n_frames = dist_arr.shape[0]

                if n_frames is None:
                    continue

                for team_name, (dist_arr, dist_cumulative_arr, vel_arr, metpow_arr, metpow_cumulative_arr, equiv_dist_arr, equiv_dist_cumulative_arr, cent_dist_arr) in team_kpi_arrays.items():
                    n_players = dist_arr.shape[1]
                    df_sorted = teamsheets[team_name].teamsheet.sort_values("xID").reset_index(drop=True)

                    dist_list = dist_arr.tolist()
                    dist_cumulative_list = dist_cumulative_arr.tolist()
                    vel_list = vel_arr.tolist()
                    metpow_list = metpow_arr.tolist()
                    metpow_cumulative_list = metpow_cumulative_arr.tolist()
                    equiv_dist_list = equiv_dist_arr.tolist()
                    equiv_dist_cumulative_list = equiv_dist_cumulative_arr.tolist()
                    cent_dist_list = cent_dist_arr.tolist()
                    for frame_idx in range(n_frames):
                        abs_frame = frame_offset + frame_idx
                        if abs_frame not in all_frame_kpis:
                            all_frame_kpis[abs_frame] = []
                        for p in range(n_players):
                            row = df_sorted.iloc[p] if p < len(df_sorted) else None
                            pid = int(row['pid']) if row is not None and pd.notna(row['pid']) else -1
                            tid = int(row['tid']) if row is not None and pd.notna(row['tid']) else -1
                            d = dist_list[frame_idx][p]
                            d_cum = dist_cumulative_list[frame_idx][p]
                            v = vel_list[frame_idx][p]
                            m = metpow_list[frame_idx][p]
                            m_cum = metpow_cumulative_list[frame_idx][p]
                            e_dist = equiv_dist_list[frame_idx][p]
                            e_dist_cum = equiv_dist_cumulative_list[frame_idx][p]
                            c_dist = cent_dist_list[frame_idx][p]
                            all_frame_kpis[abs_frame].append([
                                pid,
                                tid,
                                None if d != d else d,
                                None if d_cum != d_cum else d_cum,
                                None if v != v else v,
                                None if m != m else m,
                                None if m_cum != m_cum else m_cum,
                                None if e_dist != e_dist else e_dist,
                                None if e_dist_cum != e_dist_cum else e_dist_cum,
                                None if c_dist != c_dist else c_dist,
                            ])

                frame_offset += n_frames

        # ----------------- FRAME INDEX → MILLISECONDS
        freq = 1000.0 / framerate
        all_frame_kpis_ms = {
            int(np.rint(frame_idx * freq)): players
            for frame_idx, players in all_frame_kpis.items()
        }

        # ----------------- OUTPUT
        if pos_meta:
            meta = {
                "format": fmt,
                "kpi_names": ["distance_covered", "cumulative_distance_covered", "velocity", "metabolic_power", "cumulative_metabolic_power", "equivalent_distance", "cumulative_equivalent_distance", "centroid_distance"],
                "player_ids": pos_meta.get("player_ids", {}),
                "ref_ids": pos_meta.get("ref_ids", {}),
                "ball_ids": pos_meta.get("ball_ids", {}),
                "team_ids": pos_meta.get("team_ids", {}),
                "framerate": framerate,
                "tracking_data_id": parameters.get("tracking_data_id"),
            }
        else:
            # pos_meta is always expected; build fallback mappings from parsed teamsheets
            fallback_player_ids = {}
            fallback_team_ids = {}
            if fmt == "kinexon":
                for ts in teamsheets:
                    df = ts.teamsheet
                    if df.empty or df["group id"].iloc[0] in ball_team_ids:
                        continue
                    tid = df["tid"].iloc[0]
                    fallback_team_ids[str(tid)] = {"id": df["group id"].iloc[0]}
                    for _, row in df.iterrows():
                        if pd.notna(row.get("pid")):
                            fallback_player_ids[str(row["pid"])] = {"id": str(row["number"])}
            elif fmt == "dfl":
                for team_name, ts in teamsheets.items():
                    df = ts.teamsheet
                    if df.empty or df["tID"].iloc[0] in ball_team_ids:
                        continue
                    tid = df["tid"].iloc[0]
                    fallback_team_ids[str(tid)] = {"id": df["tID"].iloc[0]}
                    for _, row in df.iterrows():
                        if pd.notna(row.get("pid")):
                            fallback_player_ids[str(row["pid"])] = {"id": str(row["pID"])}
            meta = {
                "format": fmt,
                "kpi_names": ["distance_covered", "cumulative_distance_covered", "velocity", "metabolic_power", "cumulative_metabolic_power", "equivalent_distance", "cumulative_equivalent_distance", "centroid_distance"],
                "player_ids": fallback_player_ids,
                "ref_ids": {},
                "ball_ids": {},
                "team_ids": fallback_team_ids,
                "framerate": framerate,
                "tracking_data_id": parameters.get("tracking_data_id"),
            }

        with data_manager.create_data("KpiData") as kpi_data:
            kpi_data.tracking_data_id = parameters.get("tracking_data_id")
            kpi_data.meta_data = json.dumps(meta)
            kpi_data.kpis = json.dumps(all_frame_kpis_ms)

            self.update_callbacks(callbacks, progress=1.0)

        return {"kpi_data": kpi_data}
