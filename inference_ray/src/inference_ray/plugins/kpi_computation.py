import logging
import os
import tempfile

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
        team_id_by_orig = {}   # str(original_id) → posdata int_id
        team_id_by_name = {}   # team_name → posdata int_id
        player_id_by_orig = {}   # str(original_id) → posdata int_id
        player_id_by_name = {}   # player_name → posdata int_id
        player_id_by_number = {} # str(number) → posdata int_id

        if pos_meta:
            for int_id_str, info in pos_meta.get("team_ids", {}).items():
                int_id = int(int_id_str)
                team_id_by_orig[str(info["id"])] = int_id
                team_id_by_name[info["name"]] = int_id
            for int_id_str, info in pos_meta.get("player_ids", {}).items():
                int_id = int(int_id_str)
                player_id_by_orig[str(info["id"])] = int_id
                player_id_by_name[info["name"]] = int_id
                player_id_by_number[str(info["number"])] = int_id

        # player_id_map: combined_idx (int) -> player identifier string
        player_id_map = {}
        # team_players: team_name -> list of combined_idx values (ordered by xID)
        team_players = {}
        # ball_team_names: set of team names that represent the ball group
        ball_team_names = set()
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
                    finally:
                        os.unlink(tmp_path)

                    for i, (pos_xy, ts) in enumerate(zip(pos_data, teamsheets)):
                        team_name = ts.teamsheet['tID'].iloc[0] if not ts.teamsheet.empty else f"team_{i+1}"
                        if "ball" in team_name.lower():
                            ball_team_names.add(team_name)
                        df_ts = ts.teamsheet.sort_values("xID")
                        team_players[team_name] = []
                        for _, row in df_ts.iterrows():
                            comb_idx = len(player_id_map)
                            player_id_map[comb_idx] = str(row.get("player", row.get("sensor_id", row.get("xID", comb_idx))))
                            team_players[team_name].append(comb_idx)

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
                        if team_name == "Ball":
                            continue
                        df_ts = team_ts.teamsheet.sort_values("xID")
                        team_players[team_name] = []
                        for _, row in df_ts.iterrows():
                            comb_idx = len(player_id_map)
                            player_id_map[comb_idx] = str(row.get("player", row.get("pID", comb_idx))) # TODO: check name columns
                            team_players[team_name].append(comb_idx)


                    # Identify ball teams: present in pos_data but absent from team_players
                    for _, teams_dict in pos_data.items():
                        for tn in teams_dict:
                            if tn not in team_players:
                                ball_team_names.add(tn)

                    first_xy = next(iter(next(iter(pos_data.values())).values()))
                    framerate = int(first_xy.framerate) if first_xy.framerate else 25

                else:
                    raise ValueError(f"Unsupported format: '{fmt}'. Use 'dfl' or 'kinexon'.")

        # ----------------- TEAM ID MAPPING
        if pos_meta:
            # Use posdata team IDs: look up each team name in the reverse maps
            team_to_id = {}
            for t in list(team_players.keys()) + list(ball_team_names):
                if t in team_to_id:
                    continue
                if t in team_id_by_name:
                    team_to_id[t] = team_id_by_name[t]
                elif str(t) in team_id_by_orig:
                    team_to_id[t] = team_id_by_orig[str(t)]
                else:
                    logging.warning(f"Team '{t}' not found in posdata metadata, skipping.")
        else:
            # Fallback: 1 non-ball team → teamID 0; ball → teamID 1; 2+ non-ball teams → teamID 2, 3, ...
            non_ball_teams = [t for t in team_players if t not in ball_team_names]
            if len(non_ball_teams) == 1:
                team_to_id = {non_ball_teams[0]: 0}
            else:
                team_to_id = {t: i + 2 for i, t in enumerate(non_ball_teams)}
            for bt in ball_team_names:
                team_to_id[bt] = 1

        player_to_team_id = {}
        for tname, comb_ids in team_players.items():
            tid = team_to_id.get(tname, 0)
            for comb_idx in comb_ids:
                player_to_team_id[comb_idx] = tid

        # ----------------- PLAYER ID MAPPING (posdata-compatible)
        comb_idx_to_posdata_pid = {}
        if pos_meta:
            for comb_idx, player_str in player_id_map.items():
                # Try matching by original ID, then name, then number
                if player_str in player_id_by_orig:
                    comb_idx_to_posdata_pid[comb_idx] = player_id_by_orig[player_str]
                elif player_str in player_id_by_name:
                    comb_idx_to_posdata_pid[comb_idx] = player_id_by_name[player_str]
                elif player_str in player_id_by_number:
                    comb_idx_to_posdata_pid[comb_idx] = player_id_by_number[player_str]
                else:
                    logging.warning(f"Player '{player_str}' (comb_idx={comb_idx}) not matched in posdata metadata.")
                    comb_idx_to_posdata_pid[comb_idx] = -1

        # ----------------- COMPUTE KPIs
        all_frame_kpis = {}  # {absolute_frame_idx: [[player_id, dist, vel, metpow], ...]}
        frame_offset = 0

        if fmt == "kinexon":
            # pos_data is List[XY], one entry per group/team (including ball if tracked).
            team_kpi_arrays = {}
            n_frames = None

            for i, xy_obj in enumerate(pos_data):
                team_name = teamsheets[i].teamsheet["tID"].iloc[0] if not teamsheets[i].teamsheet.empty else f"team_{i+1}"
                if team_name in ball_team_names:
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

            if n_frames is not None:

                for team_name, (dist_arr, vel_arr, metpow_arr) in team_kpi_arrays.items():
                    if team_name in ball_team_names:
                        continue
                    team_comb_ids = team_players.get(team_name, [])
                    n_players = dist_arr.shape[1]

                    dist_list = dist_arr.tolist()
                    vel_list = vel_arr.tolist()
                    metpow_list = metpow_arr.tolist()

                    for frame_idx in range(n_frames):
                        if frame_idx not in all_frame_kpis:
                            all_frame_kpis[frame_idx] = []
                        for p in range(n_players):
                            comb_idx_p = team_comb_ids[p] if p < len(team_comb_ids) else -1
                            if pos_meta:
                                pid = comb_idx_to_posdata_pid.get(comb_idx_p, -1)
                            else:
                                pid = player_id_map.get(comb_idx_p, f"{team_name}_p{p}")
                            tid = player_to_team_id.get(comb_idx_p, team_to_id.get(team_name, 0))
                            d = dist_list[frame_idx][p]
                            v = vel_list[frame_idx][p]
                            m = metpow_list[frame_idx][p]
                            all_frame_kpis[frame_idx].append([
                                pid,
                                tid,
                                None if d != d else d,   # NaN → None (NaN != NaN is always True)
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
                    if team_name in ball_team_names:
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
                    if team_name in ball_team_names:
                        continue
                    team_comb_ids = team_players.get(team_name, [])
                    n_players = dist_arr.shape[1]

                    dist_list = dist_arr.tolist()
                    vel_list = vel_arr.tolist()
                    metpow_list = metpow_arr.tolist()

                    for frame_idx in range(n_frames):
                        abs_frame = frame_offset + frame_idx
                        if abs_frame not in all_frame_kpis:
                            all_frame_kpis[abs_frame] = []
                        for p in range(n_players):
                            comb_idx_p = team_comb_ids[p] if p < len(team_comb_ids) else -1
                            if pos_meta:
                                pid = comb_idx_to_posdata_pid.get(comb_idx_p, -1)
                            else:
                                pid = player_id_map.get(comb_idx_p, f"{team_name}_p{p}")
                            tid = player_to_team_id.get(comb_idx_p, team_to_id.get(team_name, 1))
                            d = dist_list[frame_idx][p]
                            v = vel_list[frame_idx][p]
                            m = metpow_list[frame_idx][p]
                            all_frame_kpis[abs_frame].append([
                                pid,
                                tid,
                                None if d != d else d,   # NaN → None (NaN != NaN is always True)
                                None if v != v else v,
                                None if m != m else m,
                            ])

                frame_offset += n_frames

        # ----------------- FRAME INDEX → MILLISECONDS
        freq = 1000.0 / framerate
        all_frame_kpis = {
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
            meta = {
                "format": fmt,
                "kpi_names": ["distance_covered", "velocity", "metabolic_power"],
                "player_ids": {str(k): v for k, v in player_id_map.items()},
                "team_ids": team_to_id,
                "framerate": framerate,
                "tracking_data_id": parameters.get("tracking_data_id"),
            }

        with data_manager.create_data("KpiData") as kpi_data:
            kpi_data.tracking_data_id = parameters.get("tracking_data_id")
            kpi_data.meta_data = json.dumps(meta)
            kpi_data.kpis = json.dumps(all_frame_kpis)

            self.update_callbacks(callbacks, progress=1.0)

        return {"kpi_data": kpi_data}
