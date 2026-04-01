import { defineStore } from "pinia";
import { nextTick, ref, shallowRef, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useBboxesStore } from "@/stores/bboxes";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePlayerStore } from "@/stores/player";
import { fromPosDataObject } from "../plugins/compact_posdata";

export const useTopViewStore = defineStore(
  "top_view",
  () => {
    const bboxesStore = useBboxesStore();
    const calibrationAssetStore = useCalibrationAssetStore();
    const playerStore = usePlayerStore();

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
          image: require("../assets/top-view/pitch_soccer_full.png"),
          templateCrop: { x: [0, 1], y: [0, 1] },
          widthRel: 2100 / 2260,
          heightRel: 1360 / 1519,
        },
        halfLeft: {
          title: t("sports.soccer.areas.half_left"),
          image: require("../assets/top-view/pitch_soccer_half.png"),
          templateCrop: { x: [0, 0.5], y: [0, 1] },
          widthRel: 1050 / 1210,
          heightRel: 1360 / 1519,
        },
        halfRight: {
          title: t("sports.soccer.areas.half_right"),
          image: require("../assets/top-view/pitch_soccer_half.png"),
          templateCrop: { x: [0.5, 1], y: [0, 1] },
          widthRel: 1050 / 1210,
          heightRel: 1360 / 1519,
        },
        boxToBox: {
          title: t("sports.soccer.areas.box_to_box"),
          image: require("../assets/top-view/pitch_soccer_box_to_box.png"),
          templateCrop: { x: [0.1575, 0.8425], y: [0, 1] },
          widthRel: 1440 / 1600,
          heightRel: 1360 / 1519,
        },
        doubleBoxLeft: {
          title: t("sports.soccer.areas.double_box_left"),
          image: require("../assets/top-view/pitch_soccer_double_box.png"),
          templateCrop: { x: [0, 0.315], y: [0.2025, 0.7975] },
          widthRel: 660 / 820,
          heightRel: 806 / 966,
        },
        doubleBoxRight: {
          title: t("sports.soccer.areas.double_box_right"),
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
            image: require("../assets/top-view/pitch_soccer_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 2100 / 2260,
            heightRel: 1360 / 1519,
          },
          halfLeft: {
            title: t("sports.soccer.areas.half_left"),
            image: require("../assets/top-view/pitch_soccer_half.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 1050 / 1210,
            heightRel: 1360 / 1519,
          },
          halfRight: {
            title: t("sports.soccer.areas.half_right"),
            image: require("../assets/top-view/pitch_soccer_half.png"),
            templateCrop: { x: [0.5, 1], y: [0, 1] },
            widthRel: 1050 / 1210,
            heightRel: 1360 / 1519,
          },
          boxToBox: {
            title: t("sports.soccer.areas.box_to_box"),
            image: require("../assets/top-view/pitch_soccer_box_to_box.png"),
            templateCrop: { x: [0.1575, 0.8425], y: [0, 1] },
            widthRel: 1440 / 1600,
            heightRel: 1360 / 1519,
          },
          doubleBoxLeft: {
            title: t("sports.soccer.areas.double_box_left"),
            image: require("../assets/top-view/pitch_soccer_double_box.png"),
            templateCrop: { x: [0, 0.315], y: [0.2025, 0.7975] },
            widthRel: 660 / 820,
            heightRel: 806 / 966,
          },
          doubleBoxRight: {
            title: t("sports.soccer.areas.double_box_right"),
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
            image: require("../assets/top-view/court_handball_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 2400 / 2879,
            heightRel: 1200 / 1680,
          },
          halfLeft: {
            title: t("sports.handball.areas.half_left"),
            image: require("../assets/top-view/court_handball_half_left.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 1200 / 1680,
            heightRel: 1200 / 1680,
          },
          halfRight: {
            title: t("sports.handball.areas.half_right"),
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
            image: require("../assets/top-view/court_basketball_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 1719 / 2199,
            heightRel: 915 / 1395,
          },
          halfLeft: {
            title: t("sports.basketball.areas.half_left"),
            image: require("../assets/top-view/court_basketball_half_left.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 861 / 1340,
            heightRel: 915 / 1395,
          },
          halfRight: {
            title: t("sports.basketball.areas.half_right"),
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

    // positionDataTopView holds EITHER a CompactPositionData instance (tracking data path)
    // or a plain object (bbox path). Use currentFramePlayers for single-frame access.
    const positionDataTopView = shallowRef(null);
    const metaDataTopView = shallowRef({});

    // Precomputed metadata - populated once in setPositionData() to avoid
    // multiple components independently scanning all 135k+ frames.
    const precomputedPlayerList = shallowRef([]); // [{playerId, teamId}] sorted, unique, no ball
    const precomputedPlayerIdSet = shallowRef(new Set()); // Set of all player IDs (no ball)
    const precomputedGameSections = shallowRef(new Set()); // Set of game_section values (1, 2, ...)
    const precomputedHalftimeBoundaries = shallowRef({}); // {section: {first, last}} timestamps per section

    // Whether the current positionDataTopView is a CompactPositionData instance
    const _isCompact = ref(false);

    function transformBBoxToPositionDataTopView(
      calibrationAssetId,
      bytetrackPluginId,
      updatedBboxes = null
    ) {
      calibrationAssetStore.loadCalibrationAsset(calibrationAssetId);

      if (updatedBboxes !== null) {
        bboxesStore.bboxDataActive = updatedBboxes;
        bboxesStore.bboxDataLoaded = true;
      } else {
        bboxesStore.loadBboxData(bytetrackPluginId);
      }

      if (bboxesStore.bboxDataActive && bboxesStore.bboxDataActive.length > 0) {
        // const _parsedData = JSON.parse(bboxesStore.bboxDataActive);

        const _bboxDataInterpolated = JSON.parse(bboxesStore.bboxDataActive);

        // const _bboxDataInterpolated = bboxesStore.interpolateBboxData(
        //   _parsedData,
        //   playerStore.videoFPS,
        //   30
        // );
        bboxesStore.bboxDataInterpolated = _bboxDataInterpolated;

        if (calibrationAssetStore.calibrationMatrix) {
          const newPosData = {};
          for (const [time, boxes] of Object.entries(_bboxDataInterpolated)) {
            newPosData[time] = boxes.map((b) => {
              const { x, y } = calibrationAssetStore.applyHomography(
                calibrationAssetStore.calibrationMatrix,
                { x: b[3], y: b[4] }
              );
              b[3] = x;
              b[4] = y;
              return b;
            });
          }
          positionDataTopView.value = newPosData;
          _isCompact.value = false;
        }

        const teamIdsMap = {};
        const playerIdsMap = {};
        const playerMap = new Map();
        const sections = new Set();
        const boundaries = {};
        for (const [timeKey, boxes] of Object.entries(_bboxDataInterpolated)) {
          const t = Number(timeKey);
          for (const b of boxes) {
            const playerId = b[0];
            const teamId = b[1];
            if (!(teamId in teamIdsMap)) {
              teamIdsMap[teamId] = { id: teamId, name: teamId };
            }
            if (!(playerId in playerIdsMap)) {
              playerIdsMap[playerId] = {
                id: playerId,
                name: String(playerId),
                number: playerId,
              };
            }
            if (teamId !== 1) playerMap.set(playerId, teamId);
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
          team_ids: teamIdsMap,
          player_ids: playerIdsMap,
        };
        precomputedPlayerList.value = Array.from(playerMap, ([pid, tid]) => ({
          playerId: pid,
          teamId: tid,
        })).sort((a, b) => a.playerId - b.playerId);
        precomputedPlayerIdSet.value = new Set(playerMap.keys());
        precomputedGameSections.value = sections;
        precomputedHalftimeBoundaries.value = boundaries;
      }
    }

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
      /**
       * Set position data. Accepts either:
       * - A CompactPositionData result from posdata_worker (with precomputed metadata)
       * - A plain object (for backward compatibility / bbox path)
       */
      setPositionData(posDataOrCompact, metaData, precomputed = null) {
        metaDataTopView.value = metaData;

        if (precomputed) {
          // Compact path: data is a CompactPositionData instance with precomputed metadata
          positionDataTopView.value = posDataOrCompact;
          _isCompact.value = true;
          precomputedPlayerList.value = precomputed.playerList;
          precomputedPlayerIdSet.value = precomputed.playerIdSet;
          precomputedGameSections.value = precomputed.gameSections;
          precomputedHalftimeBoundaries.value = precomputed.halftimeBoundaries;
        } else {
          // Plain-object path (bbox data or legacy)
          positionDataTopView.value = posDataOrCompact || null;
          _isCompact.value = false;

          if (posDataOrCompact && typeof posDataOrCompact === "object" && Object.keys(posDataOrCompact).length) {
            // Single-pass scan to precompute metadata (reuses fromPosDataObject but
            // we only keep the metadata, not the compact instance, to avoid double storage)
            const result = fromPosDataObject(posDataOrCompact);
            precomputedPlayerList.value = result.playerList;
            precomputedPlayerIdSet.value = result.playerIdSet;
            precomputedGameSections.value = result.gameSections;
            precomputedHalftimeBoundaries.value = result.halftimeBoundaries;
          } else {
            precomputedPlayerList.value = [];
            precomputedPlayerIdSet.value = new Set();
            precomputedGameSections.value = new Set();
            precomputedHalftimeBoundaries.value = {};
          }
        }
      },
      transformBBoxToPositionDataTopView,
      showPlayerId,
      viewPlayerId,
      precomputedPlayerList,
      precomputedPlayerIdSet,
      precomputedGameSections,
      precomputedHalftimeBoundaries,
      currentFramePlayers,
      getSubsetObject,
      getFrameAt,
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
