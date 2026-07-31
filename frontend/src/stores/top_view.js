import { defineStore } from "pinia";
import { nextTick, ref, shallowRef, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useBboxesStore } from "@/stores/bboxes";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { fromPosDataObject } from "../plugins/compact_posdata";

// Trailing index used to tag each merged tracklet with the plugin run it was physically
// loaded from (see _mergeRawBboxSources below). team_id is a mutable field that edits can
// freely change -- including across the "0 = ball" boundary -- so it can no longer be used
// to infer which backend PluginRunResult a bbox entry lives in once it's been reassigned.
// Consumers (e.g. ModalBboxUpdate.vue) should read bbox[BBOX_SOURCE_RUN_IDX] to know which
// plugin run to send edits/deletes to. Only ever set in-memory on the merged copies; never
// sent back to the backend, which re-reads its own stored blob by run id.
export const BBOX_SOURCE_RUN_IDX = 10;

export const useTopViewStore = defineStore(
  "top_view",
  () => {
    const bboxesStore = useBboxesStore();
    const calibrationAssetStore = useCalibrationAssetStore();
    const playerStore = usePlayerStore();
    const pluginRunResultStore = usePluginRunResultStore();

    const { t } = useI18n();

    const showItems = ref(false);

    const topViewSize = ref({ width: 0, height: 0, top: 0, left: 0 });
    const setTopViewSize = (size) => {
      topViewSize.value = size;
    };

    const currentAreaSize = ref("full");

    const currentSport = ref({
      key: "soccer",
      title: t("sports.soccer.title"),
      areaImage: require("../assets/top-view/pitch_soccer_full.png"),
      areas: {
        full: {
          title: t("sports.soccer.areas.full"),
          titleKey: "sports.soccer.areas.full",
          image: require("../assets/top-view/pitch_soccer_full.png"),
          templateCrop: { x: [0, 1], y: [0, 1] },
          widthRel: 2100 / 2260,
          heightRel: 1360 / 1519,
        },
        halfLeft: {
          title: t("sports.soccer.areas.half_left"),
          titleKey: "sports.soccer.areas.half_left",
          image: require("../assets/top-view/pitch_soccer_half.png"),
          templateCrop: { x: [0, 0.5], y: [0, 1] },
          widthRel: 1050 / 1210,
          heightRel: 1360 / 1519,
        },
        halfRight: {
          title: t("sports.soccer.areas.half_right"),
          titleKey: "sports.soccer.areas.half_right",
          image: require("../assets/top-view/pitch_soccer_half.png"),
          templateCrop: { x: [0.5, 1], y: [0, 1] },
          widthRel: 1050 / 1210,
          heightRel: 1360 / 1519,
        },
        boxToBox: {
          title: t("sports.soccer.areas.box_to_box"),
          titleKey: "sports.soccer.areas.box_to_box",
          image: require("../assets/top-view/pitch_soccer_box_to_box.png"),
          templateCrop: { x: [0.1575, 0.8425], y: [0, 1] },
          widthRel: 1440 / 1600,
          heightRel: 1360 / 1519,
        },
        doubleBoxLeft: {
          title: t("sports.soccer.areas.double_box_left"),
          titleKey: "sports.soccer.areas.double_box_left",
          image: require("../assets/top-view/pitch_soccer_double_box.png"),
          templateCrop: { x: [0, 0.315], y: [0.2025, 0.7975] },
          widthRel: 660 / 820,
          heightRel: 806 / 966,
        },
        doubleBoxRight: {
          title: t("sports.soccer.areas.double_box_right"),
          titleKey: "sports.soccer.areas.double_box_right",
          image: require("../assets/top-view/pitch_soccer_double_box.png"),
          templateCrop: { x: [0.685, 1], y: [0.2025, 0.7975] },
          widthRel: 660 / 820,
          heightRel: 806 / 966,
        },
      },
    });
    const sports = ref([
      {
        key: "soccer",
        title: t("sports.soccer.title"),
        areaImage: require("../assets/top-view/pitch_soccer_full.png"),
        areas: {
          full: {
            title: t("sports.soccer.areas.full"),
            titleKey: "sports.soccer.areas.full",
            image: require("../assets/top-view/pitch_soccer_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 2100 / 2260,
            heightRel: 1360 / 1519,
          },
          halfLeft: {
            title: t("sports.soccer.areas.half_left"),
            titleKey: "sports.soccer.areas.half_left",
            image: require("../assets/top-view/pitch_soccer_half.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 1050 / 1210,
            heightRel: 1360 / 1519,
          },
          halfRight: {
            title: t("sports.soccer.areas.half_right"),
            titleKey: "sports.soccer.areas.half_right",
            image: require("../assets/top-view/pitch_soccer_half.png"),
            templateCrop: { x: [0.5, 1], y: [0, 1] },
            widthRel: 1050 / 1210,
            heightRel: 1360 / 1519,
          },
          boxToBox: {
            title: t("sports.soccer.areas.box_to_box"),
            titleKey: "sports.soccer.areas.box_to_box",
            image: require("../assets/top-view/pitch_soccer_box_to_box.png"),
            templateCrop: { x: [0.1575, 0.8425], y: [0, 1] },
            widthRel: 1440 / 1600,
            heightRel: 1360 / 1519,
          },
          doubleBoxLeft: {
            title: t("sports.soccer.areas.double_box_left"),
            titleKey: "sports.soccer.areas.double_box_left",
            image: require("../assets/top-view/pitch_soccer_double_box.png"),
            templateCrop: { x: [0, 0.315], y: [0.2025, 0.7975] },
            widthRel: 660 / 820,
            heightRel: 806 / 966,
          },
          doubleBoxRight: {
            title: t("sports.soccer.areas.double_box_right"),
            titleKey: "sports.soccer.areas.double_box_right",
            image: require("../assets/top-view/pitch_soccer_double_box.png"),
            templateCrop: { x: [0.685, 1], y: [0.2025, 0.7975] },
            widthRel: 660 / 820,
            heightRel: 806 / 966,
          },
        },
      },
      {
        key: "handball",
        title: t("sports.handball.title"),
        areaImage: require("../assets/top-view/court_handball_full.png"),
        areas: {
          full: {
            title: t("sports.handball.areas.full"),
            titleKey: "sports.handball.areas.full",
            image: require("../assets/top-view/court_handball_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 2400 / 2879,
            heightRel: 1200 / 1680,
          },
          halfLeft: {
            title: t("sports.handball.areas.half_left"),
            titleKey: "sports.handball.areas.half_left",
            image: require("../assets/top-view/court_handball_half_left.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 1200 / 1680,
            heightRel: 1200 / 1680,
          },
          halfRight: {
            title: t("sports.handball.areas.half_right"),
            titleKey: "sports.handball.areas.half_right",
            image: require("../assets/top-view/court_handball_half_right.png"),
            templateCrop: { x: [0.5, 1], y: [0, 1] },
            widthRel: 1200 / 1680,
            heightRel: 1200 / 1680,
          },
        },
      },
      {
        key: "basketball",
        title: t("sports.basketball.title"),
        areaImage: require("../assets/top-view/court_basketball_full.png"),
        areas: {
          full: {
            title: t("sports.basketball.areas.full"),
            titleKey: "sports.basketball.areas.full",
            image: require("../assets/top-view/court_basketball_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 1719 / 2199,
            heightRel: 915 / 1395,
          },
          halfLeft: {
            title: t("sports.basketball.areas.half_left"),
            titleKey: "sports.basketball.areas.half_left",
            image: require("../assets/top-view/court_basketball_half_left.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 861 / 1340,
            heightRel: 915 / 1395,
          },
          halfRight: {
            title: t("sports.basketball.areas.half_right"),
            titleKey: "sports.basketball.areas.half_right",
            image: require("../assets/top-view/court_basketball_half_right.png"),
            templateCrop: { x: [0.5, 1], y: [0, 1] },
            widthRel: 861 / 1340,
            heightRel: 915 / 1395,
          },
        },
      },
      {
        key: "climbing",
        title: t("sports.climbing.title"),
        areaImage: require("../assets/top-view/area_climbing_full.png"),
        areas: {
          full: {
            title: t("sports.climbing.areas.full"),
            titleKey: "sports.climbing.areas.full",
            image: require("../assets/top-view/area_climbing_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 1600 / 1760,
            heightRel: 2000 / 2160,
          },
        },
      },
    ]);
    const onSportChange = (title, areaSize = "full") => {
      showItems.value = false;
      const sport = sports.value.find((s) => s.title === title);
      if (!sport) return;
      currentSport.value.key = sport.key;
      currentSport.value.title = sport.title;
      currentSport.value.areas = sport.areas;
      currentSport.value.areaImage =
        currentSport.value.areas[areaSize]?.image || sport.areas.full.image;
      currentAreaSize.value = areaSize;

      // Set widthRel and heightRel based on selected area size
      if (sport.areas && sport.areas[areaSize]) {
        currentSport.value.widthRel = sport.areas[areaSize].widthRel;
        currentSport.value.heightRel = sport.areas[areaSize].heightRel;
      } else {
        currentSport.value.widthRel = sport.widthRel;
        currentSport.value.heightRel = sport.heightRel;
      }

      nextTick(() => {
        showItems.value = true;
      });
    };

    const setSportFromVideo = (sportKey, areaSize = "full") => {
      const sport = sports.value.find((s) => s.key === sportKey);
      if (sport) onSportChange(sport.title, areaSize);
    };

    const showSpaceControl = ref(false);
    const viewSpaceControl = () => {
      showSpaceControl.value = !showSpaceControl.value;
      showEffectivePlayingSpace.value = false;
    };

    const showEffectivePlayingSpace = ref(false);
    const viewEffectivePlayingSpace = () => {
      showEffectivePlayingSpace.value = !showEffectivePlayingSpace.value;
      showSpaceControl.value = false;
    };

    const showHeatmap = ref(true);
    const viewHeatmap = () => {
      showHeatmap.value = !showHeatmap.value;
      showMovement.value = false;
    };

    const showMovement = ref(false);
    const viewMovement = () => {
      showMovement.value = !showMovement.value;
      showHeatmap.value = false;
    };

    const showPlayerId = ref(false);
    const viewPlayerId = () => {
      showPlayerId.value = !showPlayerId.value;
    };

    const mirrorXY = ref(false);
    const viewMirrorXY = () => {
      mirrorXY.value = !mirrorXY.value;
    };

    // positionDataTopView holds EITHER a CompactPositionData instance (tracking data path)
    // or a plain object (bbox path). Use currentFramePlayers for single-frame access.
    const positionDataTopView = shallowRef(null);
    const metaDataTopView = shallowRef({});

    // Precomputed metadata - populated once in setPositionData() to avoid
    // multiple components independently scanning all 135k+ frames.
    // Kinds split by team_id: 0=ball, 1=inactive, 2=ref, ≥3=active player.
    const precomputedPlayerList = shallowRef([]); // active players only (team_id ≥ 3)
    const precomputedRefList = shallowRef([]);
    const precomputedBallList = shallowRef([]);
    const precomputedInactiveList = shallowRef([]);
    const precomputedPlayerIdSet = shallowRef(new Set()); // active players only
    const precomputedGameSections = shallowRef(new Set()); // Set of game_section values (1, 2, ...)
    const precomputedHalftimeBoundaries = shallowRef({}); // {section: {first, last}} timestamps per section

    // Toggle for entity kinds in the top-view overlay (refs/inactive default off).
    const visibleEntityKinds = ref({ player: true, ref: false, ball: true, rest: false });
    const toggleEntityKind = (kind) => {
      visibleEntityKinds.value = {
        ...visibleEntityKinds.value,
        [kind]: !visibleEntityKinds.value[kind],
      };
    };

    // Lookup helpers: pick the right meta dict based on team_id semantics.
    const _kindFromTeamId = (tid) => {
      const n = Number(tid);
      if (n === 0) return "ball";
      if (n === 2) return "ref";
      if (n === 1) return "rest";
      return "player";
    };
    const getEntityName = (entityId, teamId) => {
      const meta = metaDataTopView.value;
      if (!meta) return String(entityId);
      const kind = _kindFromTeamId(teamId);
      const dictKey = kind === "ref" ? "ref_ids" : kind === "ball" ? "ball_ids" : "player_ids";
      return meta?.[dictKey]?.[entityId]?.name ?? String(entityId);
    };
    const getEntityNumber = (entityId, teamId) => {
      const meta = metaDataTopView.value;
      if (!meta) return entityId;
      const kind = _kindFromTeamId(teamId);
      const dictKey = kind === "ref" ? "ref_ids" : kind === "ball" ? "ball_ids" : "player_ids";
      const num = meta?.[dictKey]?.[entityId]?.number;
      return num != null ? num : entityId;
    };

    // Whether the current positionDataTopView is a CompactPositionData instance
    const _isCompact = ref(false);

    // Applies the calibration homography to a plain-object bbox dataset (time -> [tracklet, ...]),
    // matching the tracklet layout produced by bytetrack/object_tracker (b[3]/b[4] = x/y).
    function _applyHomographyToBboxData(bboxData) {
      if (!calibrationAssetStore.calibrationMatrix) return null;
      const transformed = {};
      for (const [time, boxes] of Object.entries(bboxData)) {
        transformed[time] = boxes.map((b) => {
          const { x, y } = calibrationAssetStore.applyHomography(
            calibrationAssetStore.calibrationMatrix,
            { x: b[3], y: b[4] }
          );
          b[3] = x;
          b[4] = 1 - y;
          return b;
        });
      }
      return transformed;
    }

    // Combines the player run's raw bboxes (bboxesStore.bboxDataActive) with the
    // separately-tracked ball run's raw bboxes (bboxesStore.bboxBallDataActive), both in
    // video-space (b[5..8] = x,y,w,h), keyed by frame time. Re-parses fresh each call so
    // callers can safely pass the result into _applyHomographyToBboxData (which mutates
    // its input in place) without corrupting bboxDataInterpolated.
    function _mergeRawBboxSources() {
      const tagSource = (boxes, runId) =>
        boxes.map((b) => {
          b[BBOX_SOURCE_RUN_IDX] = runId;
          return b;
        });

      const playerRaw = bboxesStore.bboxDataActive ? JSON.parse(bboxesStore.bboxDataActive) : {};
      const ballRaw = bboxesStore.bboxBallDataActive
        ? JSON.parse(bboxesStore.bboxBallDataActive)
        : {};

      const merged = {};
      for (const [time, boxes] of Object.entries(playerRaw)) {
        merged[time] = tagSource(boxes, bboxesStore.bboxPluginRunId);
      }
      for (const [time, boxes] of Object.entries(ballRaw)) {
        const tagged = tagSource(boxes, bboxesStore.bboxBallPluginRunId);
        merged[time] = merged[time] ? [...merged[time], ...tagged] : tagged;
      }
      return merged;
    }

    // Combines player + ball meta_data (team_ids/player_ids/ref_ids/ball_ids), so neither
    // run's entity names/numbers get dropped when the other run is (re)loaded or edited.
    function _combinedStoredMeta() {
      const playerMeta = bboxesStore.bboxMetaData ? JSON.parse(bboxesStore.bboxMetaData) : {};
      const ballMeta = bboxesStore.bboxBallMetaData ? JSON.parse(bboxesStore.bboxBallMetaData) : {};
      return {
        team_ids: { ...(playerMeta.team_ids ?? {}), ...(ballMeta.team_ids ?? {}) },
        player_ids: { ...(playerMeta.player_ids ?? {}), ...(ballMeta.player_ids ?? {}) },
        ref_ids: { ...(playerMeta.ref_ids ?? {}), ...(ballMeta.ref_ids ?? {}) },
        ball_ids: { ...(playerMeta.ball_ids ?? {}), ...(ballMeta.ball_ids ?? {}) },
      };
    }

    // Rebuilds bboxDataInterpolated (video overlay) and positionDataTopView (pitch view)
    // from the current player + ball raw sources. Called after loading either run and
    // after editing/deleting a bbox in either run, so the merged view never goes stale.
    function _applyMergedBboxData() {
      bboxesStore.bboxDataInterpolated = _mergeRawBboxSources();

      const newPosData = _applyHomographyToBboxData(_mergeRawBboxSources());
      if (newPosData) {
        positionDataTopView.value = newPosData;
        _isCompact.value = false;
      }
    }

    // Rebuilds metaDataTopView and the four precomputed*List aggregates from the current
    // positionDataTopView.value (plain-object path only). Shared by the initial bbox load
    // and by mergeBallTracking, so both end up with consistent aggregates.
    function _recomputeAggregates(storedMeta) {
      const playerMap = new Map();
      const refMap = new Map();
      const ballMap = new Map();
      const inactiveMap = new Map();
      const sections = new Set();
      const boundaries = {};
      for (const [timeKey, boxes] of Object.entries(positionDataTopView.value ?? {})) {
        const t = Number(timeKey);
        for (const b of boxes) {
          const tid = b[1];
          if (tid === 0) {
            ballMap.set(b[0], tid);
            refMap.delete(b[0]);
            inactiveMap.delete(b[0]);
            playerMap.delete(b[0]);
          } else if (tid === 2) {
            refMap.set(b[0], tid);
            ballMap.delete(b[0]);
            inactiveMap.delete(b[0]);
            playerMap.delete(b[0]);
          } else if (tid === 1) {
            if (!ballMap.has(b[0]) && !refMap.has(b[0]) && !playerMap.has(b[0]))
              inactiveMap.set(b[0], tid);
          } else {
            playerMap.set(b[0], tid);
            ballMap.delete(b[0]);
            refMap.delete(b[0]);
            inactiveMap.delete(b[0]);
          }
          const gs = b[2];
          sections.add(gs);
          if (!boundaries[gs]) {
            boundaries[gs] = { first: t, last: t };
          } else {
            if (t < boundaries[gs].first) boundaries[gs].first = t;
            if (t > boundaries[gs].last) boundaries[gs].last = t;
          }
        }
      }
      metaDataTopView.value = {
        team_ids: storedMeta.team_ids ?? {},
        player_ids: storedMeta.player_ids ?? {},
        ref_ids: storedMeta.ref_ids ?? {},
        ball_ids: storedMeta.ball_ids ?? {},
      };
      const _toList = (m) =>
        Array.from(m, ([pid, tid]) => ({ playerId: pid, teamId: tid })).sort(
          (a, b) => a.playerId - b.playerId
        );
      precomputedPlayerList.value = _toList(playerMap);
      precomputedRefList.value = _toList(refMap);
      precomputedBallList.value = _toList(ballMap);
      precomputedInactiveList.value = _toList(inactiveMap);
      precomputedPlayerIdSet.value = new Set(playerMap.keys());
      precomputedGameSections.value = sections;
      precomputedHalftimeBoundaries.value = boundaries;
    }

    async function transformBBoxToPositionDataTopView(
      calibrationAssetId,
      bytetrackPluginId,
      updatedBboxes = null
    ) {
      calibrationAssetStore.loadCalibrationAsset(calibrationAssetId);

      if (updatedBboxes !== null) {
        bboxesStore.bboxDataActive = updatedBboxes;
        bboxesStore.bboxDataLoaded = true;
      } else {
        await bboxesStore.loadBboxData(bytetrackPluginId);
      }

      if (bboxesStore.bboxDataActive && bboxesStore.bboxDataActive.length > 0) {
        _applyMergedBboxData();
        _recomputeAggregates(_combinedStoredMeta());
      }
    }

    // Merges an optional, separately-run ball-tracking result (object_tracker plugin run
    // without a tracker, filtered to the ball class) into the currently loaded
    // positionDataTopView and bboxesStore.bboxDataInterpolated, so both the pitch view and
    // the video overlay (VideoPlayer.vue) render the ball. The ball run's own state
    // (bboxBallDataActive/bboxBallMetaData/bboxBallPluginRunId) is tracked separately from
    // bboxesStore.bboxDataActive/bboxPluginRunId, which must keep pointing at the player
    // run for bbox editing. Plain-object path only (no manual/Compact merge).
    async function mergeBallTracking(calibrationAssetId, ballPluginRunId) {
      if (!ballPluginRunId) return;

      calibrationAssetStore.loadCalibrationAsset(calibrationAssetId);

      const results = await pluginRunResultStore.forPluginRunWithData(
        ballPluginRunId,
        playerStore.videoId
      );
      const ballResult = results.find((r) => r.data?.bboxes !== undefined);
      if (!ballResult) return;

      bboxesStore.bboxBallPluginRunId = ballPluginRunId;
      bboxesStore.bboxBallDataActive = ballResult.data.bboxes;
      bboxesStore.bboxBallMetaData = ballResult.data.meta_data ?? null;

      _applyMergedBboxData();
      _recomputeAggregates(_combinedStoredMeta());
    }

    // Refreshes the ball run's raw bboxes/meta after an edit or delete targeting the ball
    // plugin run (see bboxesStore.updateBboxData/deleteBboxData), then rebuilds the merged
    // view so the change shows up immediately without dropping the player run's data.
    function refreshBallBboxData(updatedBboxes, updatedMeta) {
      bboxesStore.bboxBallDataActive = updatedBboxes;
      bboxesStore.bboxBallMetaData = updatedMeta ?? null;

      _applyMergedBboxData();
      _recomputeAggregates(_combinedStoredMeta());
    }

    // team_clustering writes raw cluster indices (0..K-1, or -1 for HDBSCAN noise) into
    // TeamsData, not the app's TeamId convention (0=ball, 1=bystander, 2=referee, 3+=teams,
    // see inference_ray/.../object_tracker.py's TeamId enum and visualization.js's
    // teamColorMapping). Cluster 0/1 must not be written to b[1] as-is, or players would be
    // misclassified as ball/bystander -- offset active clusters into the team range and map
    // noise to "bystander" (no confident team assignment).
    const TEAM_CLUSTER_LABEL_OFFSET = 3;
    const TEAM_CLUSTER_NOISE_TEAM_ID = 1;

    // Applies a separately-run team_clustering result (TeamsData: {frame_time: {track_id:
    // cluster_label}}) onto the currently loaded player run by overwriting b[1] (team_id) in
    // bboxesStore.bboxDataActive. This is a ONE-TIME mutation of the source, not a live
    // overlay like mergeBallTracking -- ModalBboxUpdate.vue lets users manually correct
    // individual team assignments afterwards, and those edits must not be reverted the next
    // time _applyMergedBboxData() recomputes (e.g. after an unrelated bbox edit elsewhere).
    async function mergeTeamAssignment(teamClusteringPluginRunId) {
      if (!teamClusteringPluginRunId) return;

      const results = await pluginRunResultStore.forPluginRunWithData(
        teamClusteringPluginRunId,
        playerStore.videoId
      );
      const teamsResult = results.find((r) => r.data?.teams_data !== undefined);
      if (!teamsResult) return;

      const teamsMapping = teamsResult.data.teams_data;

      const playerRaw = bboxesStore.bboxDataActive ? JSON.parse(bboxesStore.bboxDataActive) : {};
      for (const [frameTime, boxes] of Object.entries(playerRaw)) {
        const frameAssignments = teamsMapping[frameTime];
        if (!frameAssignments) continue;

        for (const b of boxes) {
          const label = frameAssignments[b[0]];
          if (label === undefined || label === null) continue;

          b[1] = label < 0 ? TEAM_CLUSTER_NOISE_TEAM_ID : label + TEAM_CLUSTER_LABEL_OFFSET;
        }
      }
      bboxesStore.bboxDataActive = JSON.stringify(playerRaw);

      _applyMergedBboxData();
      _recomputeAggregates(_combinedStoredMeta());
    }

    // Applies a separately-run osnet_reid result (ReIDData: {frame_time: {old_track_id:
    // new_reid_id}}) onto the currently loaded player run by overwriting b[0] (track_id/
    // player_id) in bboxesStore.bboxDataActive. Like mergeTeamAssignment, this is a ONE-TIME
    // mutation of the source and must run AFTER mergeTeamAssignment, since team_clustering's
    // mapping is keyed by the ORIGINAL object_tracker track_ids -- swapping b[0] first would
    // break that lookup. The raw reid mapping is also stashed on bboxesStore.bboxReidMapping
    // so bbox edits/deletes (updateBboxData/deleteBboxData) can translate the currently
    // displayed (new) id back to the original track_id the backend still knows about.
    async function mergeReid(reidPluginRunId) {
      if (!reidPluginRunId) return;

      const results = await pluginRunResultStore.forPluginRunWithData(
        reidPluginRunId,
        playerStore.videoId
      );
      const reidResult = results.find((r) => r.data?.mapping !== undefined);
      if (!reidResult) return;

      const reidMapping = reidResult.data.mapping;
      bboxesStore.bboxReidMapping = reidMapping;

      const playerRaw = bboxesStore.bboxDataActive ? JSON.parse(bboxesStore.bboxDataActive) : {};
      const newPlayerIds = new Set();
      for (const [frameTime, boxes] of Object.entries(playerRaw)) {
        const frameMapping = reidMapping[frameTime];
        if (!frameMapping) continue;

        for (const b of boxes) {
          const newId = frameMapping[b[0]];
          if (newId === undefined || newId === null) continue;

          b[0] = newId;
          newPlayerIds.add(newId);
        }
      }
      bboxesStore.bboxDataActive = JSON.stringify(playerRaw);

      // player_ids meta is keyed by track_id -- entries under the old ids are now orphaned.
      // Rebuild entries for the new (reid) ids using the same default naming convention as
      // the backend (object_tracker.py: name=str(pid), number=pid). team_id is intentionally
      // left alone here; team assignment already ran (and wrote b[1]) before this merge.
      const playerMeta = bboxesStore.bboxMetaData ? JSON.parse(bboxesStore.bboxMetaData) : {};
      const rebuiltPlayerIds = {};
      for (const pid of newPlayerIds) {
        rebuiltPlayerIds[pid] = playerMeta.player_ids?.[pid] ?? {
          id: pid,
          name: String(pid),
          number: pid,
        };
      }
      playerMeta.player_ids = { ...(playerMeta.player_ids ?? {}), ...rebuiltPlayerIds };
      bboxesStore.bboxMetaData = JSON.stringify(playerMeta);

      _applyMergedBboxData();
      _recomputeAggregates(_combinedStoredMeta());
    }

    const showSportZones = ref(false);
    const toggleSportZones = () => {
      showSportZones.value = !showSportZones.value;
    };

    const gridConfig = {
      longitudinal: {
        options: [0, 3, 5],
        positions: {
          3: [0.2025, 0.7955],
          5: [0.2025, 0.365, 0.635, 0.7955],
        },
      },
      transverse: {
        options: [0, 3, 5],
        positions: {
          3: [0.33, 0.67],
          5: [0.1575, 0.33, 0.67, 0.8425],
        },
      },
    };
    const gridLongitudinal = ref(0);
    const gridTransverse = ref(0);
    const gridLines = computed(() => ({
      horizontal: gridConfig.longitudinal.positions[gridLongitudinal.value] ?? [],
      vertical: gridConfig.transverse.positions[gridTransverse.value] ?? [],
    }));

    const currentTime = ref(0);
    const currentTimeOffset = ref(0);

    // Pre-sorted key list, recomputed only when positionDataTopView changes
    const sortedFrameKeys = computed(() => {
      const data = positionDataTopView.value;
      if (!data) return [];
      if (_isCompact.value) {
        return data.getTimestampArray();
      }
      return Object.keys(data)
        .map(Number)
        .sort((a, b) => a - b);
    });

    const currentFrameKey = computed(() => {
      const data = positionDataTopView.value;
      if (!data) return undefined;

      const target =
        Number(playerStore.isSynced ? playerStore.currentTime : currentTime.value) +
        Number(currentTimeOffset.value);

      if (_isCompact.value) {
        const idx = data.getFrameIndex(target);
        return idx >= 0 ? data.getTimestamp(idx) : undefined;
      }

      // Fallback for plain-object mode (bbox path)
      const keys = sortedFrameKeys.value;
      if (!keys.length) return undefined;
      let lo = 0;
      let hi = keys.length - 1;
      if (target < keys[0]) return keys[0];
      if (target >= keys[hi]) return keys[hi];
      while (lo < hi) {
        const mid = (lo + hi + 1) >>> 1;
        if (keys[mid] <= target) {
          lo = mid;
        } else {
          hi = mid - 1;
        }
      }
      return keys[lo];
    });

    // Materialized players for the current frame. Components should use this
    // instead of positionDataTopView[frameKey] for single-frame access.
    const currentFramePlayers = computed(() => {
      const data = positionDataTopView.value;
      const fk = currentFrameKey.value;
      if (!data || fk === undefined) return [];
      if (_isCompact.value) {
        return data.getFrame(fk);
      }
      return data[fk] || [];
    });

    /**
     * Get a plain-object subset of position data for a time range.
     * Used by workers that need bulk data (heatmap, running distance).
     */
    function getSubsetObject(startMs, endMs) {
      const data = positionDataTopView.value;
      if (!data) return {};
      if (_isCompact.value) {
        return data.toSubsetObject(startMs, endMs);
      }
      // Plain-object fallback
      const result = {};
      for (const key of Object.keys(data)) {
        const t = Number(key);
        if (t >= startMs && t <= endMs) result[key] = data[key];
      }
      return result;
    }

    /**
     * Get a frame's players by timestamp. Use for indexed access
     * when currentFrameKey isn't what you need.
     */
    function getFrameAt(timestampMs) {
      const data = positionDataTopView.value;
      if (!data) return [];
      if (_isCompact.value) {
        return data.getFrame(timestampMs);
      }
      return data[timestampMs] || [];
    }

    function setPositionData(posDataOrCompact, metaData, precomputed = null) {
      metaDataTopView.value = metaData;

      if (precomputed) {
        // Compact path: data is a CompactPositionData instance with precomputed metadata
        positionDataTopView.value = posDataOrCompact;
        _isCompact.value = true;
        precomputedPlayerList.value = precomputed.playerList;
        precomputedRefList.value = precomputed.refList ?? [];
        precomputedBallList.value = precomputed.ballList ?? [];
        precomputedInactiveList.value = precomputed.inactiveList ?? [];
        precomputedPlayerIdSet.value = precomputed.playerIdSet;
        precomputedGameSections.value = precomputed.gameSections;
        precomputedHalftimeBoundaries.value = precomputed.halftimeBoundaries;
      } else {
        // Plain-object path (bbox data or legacy)
        positionDataTopView.value = posDataOrCompact || null;
        _isCompact.value = false;

        if (
          posDataOrCompact &&
          typeof posDataOrCompact === "object" &&
          Object.keys(posDataOrCompact).length
        ) {
          // Single-pass scan to precompute metadata (reuses fromPosDataObject but
          // we only keep the metadata, not the compact instance, to avoid double storage)
          const result = fromPosDataObject(posDataOrCompact);
          precomputedPlayerList.value = result.playerList;
          precomputedRefList.value = result.refList;
          precomputedBallList.value = result.ballList;
          precomputedInactiveList.value = result.inactiveList;
          precomputedPlayerIdSet.value = result.playerIdSet;
          precomputedGameSections.value = result.gameSections;
          precomputedHalftimeBoundaries.value = result.halftimeBoundaries;
        } else {
          precomputedPlayerList.value = [];
          precomputedRefList.value = [];
          precomputedBallList.value = [];
          precomputedInactiveList.value = [];
          precomputedPlayerIdSet.value = new Set();
          precomputedGameSections.value = new Set();
          precomputedHalftimeBoundaries.value = {};
        }
      }
    }

    return {
      topViewSize,
      setTopViewSize,
      currentSport,
      sports,
      onSportChange,
      setSportFromVideo,
      currentAreaSize,
      showItems,
      showSpaceControl,
      viewSpaceControl,
      showEffectivePlayingSpace,
      viewEffectivePlayingSpace,
      showHeatmap,
      viewHeatmap,
      showMovement,
      viewMovement,
      positionDataTopView,
      metaDataTopView,
      setPositionData,
      transformBBoxToPositionDataTopView,
      mergeBallTracking,
      mergeTeamAssignment,
      mergeReid,
      refreshBallBboxData,
      showPlayerId,
      viewPlayerId,
      mirrorXY,
      viewMirrorXY,
      precomputedPlayerList,
      precomputedRefList,
      precomputedBallList,
      precomputedInactiveList,
      precomputedPlayerIdSet,
      precomputedGameSections,
      precomputedHalftimeBoundaries,
      visibleEntityKinds,
      toggleEntityKind,
      getEntityName,
      getEntityNumber,
      currentFramePlayers,
      getSubsetObject,
      getFrameAt,
      showSportZones,
      toggleSportZones,
      gridConfig,
      gridLongitudinal,
      gridTransverse,
      gridLines,
      currentTime,
      currentFrameKey,
      sortedFrameKeys,
      currentTimeOffset,
    };
  },
  {
    persist: {
      pick: ["currentSport", "currentAreaSize"],
      storage: sessionStorage,
    },
  }
);
