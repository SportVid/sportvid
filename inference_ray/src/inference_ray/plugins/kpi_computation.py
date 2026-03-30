import logging
import os
import tempfile

import pandas as pd
from typing import Callable, Dict

from data import KpiData, TrackingData
from data import DataManager, Data

from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {
    "delimiter": ";"
}

requires = {
    "tracking_data": TrackingData
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
        from floodlight.models.kinematics import DistanceModel, VelocityModel
        from floodlight.models.kinetics import MetabolicPowerModel

        if "format" not in parameters:
            raise ValueError("'format' is required for plugin execution.")

        fmt = parameters["format"]

        # Load posdata metadata if available
        pos_meta_raw = parameters.get("pos_meta", "")
        pos_meta = json.loads(pos_meta_raw) if pos_meta_raw else None

        # Build reverse lookups from posdata metadata
        team_id_by_orig = {}   # original_id → posdata int_id
        player_id_by_orig = {}  # original_id → posdata int_id

        if pos_meta:
            for int_id_str, info in pos_meta.get("team_ids", {}).items():
                team_id_by_orig[info["id"]] = int(int_id_str)
            for int_id_str, info in pos_meta.get("player_ids", {}).items():
                player_id_by_orig[info["id"]] = int(int_id_str)

        # ball_team_ids: set of original group/team id values that represent the ball
        ball_team_ids = set()
        framerate = None

        # ----------------- PARSING
        with inputs["tracking_data"] as input_data:
            with input_data.open_file() as t_data:
                if fmt == "kinexon":
                    with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as tmp:
                        tmp.write(t_data.read())
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
                            if tid == 1:
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
                            if tid == 1:
                                ball_team_ids.add(group_id_val)
                                continue

                        df["pid"] = df["pID"].map(player_id_by_orig) if pos_meta else df["pID"].astype(str)
                        df["tid"] = tid
                        teamsheets[team_name].teamsheet = df

                    first_xy = next(iter(next(iter(pos_data.values())).values()))
                    framerate = int(first_xy.framerate) if first_xy.framerate else 25

                else:
                    raise ValueError(f"Unsupported format: '{fmt}'. Use 'dfl' or 'kinexon'.")

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

                dist_mod = DistanceModel()
                vel_mod = VelocityModel()
                metpow_mod = MetabolicPowerModel()

                dist_mod.fit(xy_obj)
                vel_mod.fit(xy_obj)
                metpow_mod.fit(xy_obj)

                dist_arr = np.array(dist_mod.cumulative_distance_covered()).round(2)  # (T, N)
                vel_arr = np.array(vel_mod.velocity()).round(2)                       # (T, N)
                metpow_arr = np.array(metpow_mod.metabolic_power()).round(2)          # (T, N)

                team_kpi_arrays[i] = (df_ts.sort_values("xID").reset_index(drop=True), dist_arr, vel_arr, metpow_arr)
                if n_frames is None:
                    n_frames = dist_arr.shape[0]

            if n_frames is not None:
                for i, (df_sorted, dist_arr, vel_arr, metpow_arr) in team_kpi_arrays.items():
                    n_players = dist_arr.shape[1]

                    dist_list = dist_arr.tolist()
                    vel_list = vel_arr.tolist()
                    metpow_list = metpow_arr.tolist()

                    for frame_idx in range(n_frames):
                        if frame_idx not in all_frame_kpis:
                            all_frame_kpis[frame_idx] = []
                        for p in range(n_players):
                            row = df_sorted.iloc[p] if p < len(df_sorted) else None
                            pid = int(row['pid']) if row is not None and pd.notna(row['pid']) else -1
                            tid = int(row['tid']) if row is not None and pd.notna(row['tid']) else -1
                            d = dist_list[frame_idx][p]
                            v = vel_list[frame_idx][p]
                            m = metpow_list[frame_idx][p]
                            all_frame_kpis[frame_idx].append([
                                pid,
                                tid,
                                None if d != d else d,
                                None if v != v else v,
                                None if m != m else m,
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

                    dist_mod = DistanceModel()
                    vel_mod = VelocityModel()
                    metpow_mod = MetabolicPowerModel()

                    dist_mod.fit(xy_obj)
                    vel_mod.fit(xy_obj)
                    metpow_mod.fit(xy_obj)

                    dist_arr = np.array(dist_mod.cumulative_distance_covered()).round(2)  # (T, N)
                    vel_arr = np.array(vel_mod.velocity()).round(2)                       # (T, N)
                    metpow_arr = np.array(metpow_mod.metabolic_power()).round(2)          # (T, N)

                    team_kpi_arrays[team_name] = (dist_arr, vel_arr, metpow_arr)
                    if n_frames is None:
                        n_frames = dist_arr.shape[0]

                if n_frames is None:
                    continue

                for team_name, (dist_arr, vel_arr, metpow_arr) in team_kpi_arrays.items():
                    n_players = dist_arr.shape[1]
                    df_sorted = teamsheets[team_name].teamsheet.sort_values("xID").reset_index(drop=True)

                    dist_list = dist_arr.tolist()
                    vel_list = vel_arr.tolist()
                    metpow_list = metpow_arr.tolist()

                    for frame_idx in range(n_frames):
                        abs_frame = frame_offset + frame_idx
                        if abs_frame not in all_frame_kpis:
                            all_frame_kpis[abs_frame] = []
                        for p in range(n_players):
                            row = df_sorted.iloc[p] if p < len(df_sorted) else None
                            pid = int(row['pid']) if row is not None and pd.notna(row['pid']) else -1
                            tid = int(row['tid']) if row is not None and pd.notna(row['tid']) else -1
                            d = dist_list[frame_idx][p]
                            v = vel_list[frame_idx][p]
                            m = metpow_list[frame_idx][p]
                            all_frame_kpis[abs_frame].append([
                                pid,
                                tid,
                                None if d != d else d,
                                None if v != v else v,
                                None if m != m else m,
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
                "kpi_names": ["distance_covered", "velocity", "metabolic_power"],
                "player_ids": pos_meta["player_ids"],
                "team_ids": pos_meta["team_ids"],
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
                "kpi_names": ["distance_covered", "velocity", "metabolic_power"],
                "player_ids": fallback_player_ids,
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
