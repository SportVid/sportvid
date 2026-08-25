import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { throttle } from "lodash";
import axios from "../plugins/axios";
import config from "../../app.config";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "./top_view";
import { useBboxesStore } from "./bboxes";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useVisualizationStore } from "@/stores/visualization";
import { usePosdataWorkerStore } from "@/stores/posdata_worker";
import { isInSportZone } from "@/plugins/sport_zones";

function isInSportZoneUtil(z, x, y) {
  return isInSportZone(z.sportKey, z.zoneId, x, y, z.half);
}

export const usePositionDataStore = defineStore(
  "position_data",
  () => {
    const playerStore = usePlayerStore();
    const topViewStore = useTopViewStore();
    const bboxesStore = useBboxesStore();
    const calibrationAssetStore = useCalibrationAssetStore();
    const visualizationStore = useVisualizationStore();

    const positionDataList = ref([]);
    const positionDataId = ref(null);
    // Which source ModalPositionDataSelect.vue's confirmSelection last picked —
    // 'manual' | 'bytetrack' | 'object_tracker' | null (nothing chosen yet).
    // Persisted (see this store's `persist` option) so restoreFromCache knows
    // which of the two restore paths below to take after a reload; it's the
    // only thing here that isn't itself a positionDataId, hence living in
    // this store rather than bboxesStore/calibrationAssetStore.
    const positionDataMode = ref(null);
    const isRestoringPosData = ref(false);

    const isUploading = ref(false);
    const progress = ref(0);

    const positionDataUploadSuccess = ref(false);
    const positionDataRenameSuccess = ref(false);
    const positionDataDeleteSuccess = ref(false);

    const provider = [
      { name: "Kinexon", id: "kinexon" },
      { name: "DFL", id: "dfl" },
    ];

    const loadPositionDataList = async () => {
      try {
        const params = { video_id: playerStore.videoId };
        const res = await axios.get(`${config.API_LOCATION}/tracking_data/list`, { params });
        if (res.data.status === "ok") {
          positionDataList.value = res.data.entries;
        }
      } catch (error) {
        console.error("Failed to list tracking data:", error);
      }
    };

    const loadPositionData = async (id) => {
      const selectedPositionData = positionDataList.value.find((data) => data.id === id);
      if (!selectedPositionData) return;

      positionDataId.value = id;
      bboxesStore.bboxDataActive = {};
      bboxesStore.bboxDataInterpolated = {};

      const workerStore = usePosdataWorkerStore();

      // 1. Try in-memory cache (instant, no network)
      const cached = workerStore.getCached(id);
      if (cached) {
        topViewStore.setPositionData(cached.compact, cached.metaData, {
          playerList: cached.playerList,
          refList: cached.refList,
          ballList: cached.ballList,
          inactiveList: cached.inactiveList,
          playerIdSet: cached.playerIdSet,
          gameSections: cached.gameSections,
          halftimeBoundaries: cached.halftimeBoundaries,
        });
        setTimeRangeToFullMatch();
        return;
      }

      // 2. Chunk-load from backend (progressive, with progress bar)
      const result = await workerStore.loadChunked(id, playerStore.videoId);
      if (result) {
        topViewStore.setPositionData(result.compact, result.metaData, {
          playerList: result.playerList,
          refList: result.refList,
          ballList: result.ballList,
          inactiveList: result.inactiveList,
          playerIdSet: result.playerIdSet,
          gameSections: result.gameSections,
          halftimeBoundaries: result.halftimeBoundaries,
        });
        setTimeRangeToFullMatch();
      }
    };

    const uploadPositionData = async (params) => {
      if (!params) return;
      isUploading.value = true;
      try {
        const formData = new FormData();
        formData.append("video_id", playerStore.videoId);
        formData.append("title", params.title);
        formData.append("format", params.format);
        formData.append("file", params.file);
        formData.append("meta_data", params.metaData);
        formData.append("delimiter", params.delimiter);
        formData.append("origin", params.origin);
        formData.append("team_id_ball", params.teamIdBall);
        formData.append("team_id_ref", params.teamIdRef ?? "");
        formData.append("fps", params.fps);

        const res = await axios.post(`${config.API_LOCATION}/tracking_data/upload`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (event) => {
            if (event.lengthComputable) {
              progress.value = Math.round((event.loaded * 100) / event.total);
            }
          },
        });

        if (res.data.status === "ok") {
          positionDataUploadSuccess.value = true;
          await loadPositionDataList();
        }
      } catch (error) {
        console.error("Failed to upload position data:", error);
      } finally {
        isUploading.value = false;
        progress.value = 0;
      }
    };

    const renamePositionData = async (id, newName) => {
      if (!id || !newName) return;
      try {
        const res = await axios.post(`${config.API_LOCATION}/tracking_data/rename`, {
          id,
          name: newName,
        });
        if (res.data.status === "ok") {
          positionDataRenameSuccess.value = true;
          await loadPositionDataList();
        }
      } catch (error) {
        console.error("Failed to rename position data:", error);
      } finally {
      }
    };

    const deletePositionData = async (id) => {
      if (!id) return;
      try {
        const res = await axios.post(`${config.API_LOCATION}/tracking_data/delete`, {
          id,
        });
        if (res.data.status === "ok") {
          positionDataDeleteSuccess.value = true;
          await loadPositionDataList();
          if (
            positionDataId.value &&
            !positionDataList.value.find((d) => d.id === positionDataId.value)
          ) {
            positionDataId.value = null;
            topViewStore.setPositionData(null, {});
          }
        }
      } catch (error) {
        console.error("Failed to delete position data:", error);
      } finally {
      }
    };

    function isInAnyZone(x, y, zones) {
      if (!zones || zones.length === 0) return false;
      for (const z of zones) {
        if (z.sportZone) {
          if (isInSportZoneUtil(z, x, y)) return true;
          continue;
        }
        if (x >= z.x0 && x <= z.x1 && y >= z.y0 && y <= z.y1) return true;
      }
      return false;
    }

    function calculateRunningDistances(selectedPlayerIds, startFrame, endFrame, zones = []) {
      const distancesByPlayerId = new Map();

      // Use pre-sorted frame keys instead of creating new 135k-element array
      const allTimes = topViewStore.sortedFrameKeys;

      const timeRange = allTimes.filter((t) => t >= startFrame && t <= endFrame);

      const allPlayersSet = new Map();

      for (let ti = 0; ti < allTimes.length; ti++) {
        const players = topViewStore.getFrameAt(allTimes[ti]);
        if (!players || !players.length) continue;
        for (const p of players) {
          if (p[1] < 3) continue;
          if (
            (visualizationStore.showAggregatedFirst && p[2] !== 1) ||
            (visualizationStore.showAggregatedSecond && p[2] !== 2)
          ) {
            continue;
          }
          if (!allPlayersSet.has(p[0])) {
            allPlayersSet.set(p[0], { player_id: p[0], team_id: p[1] });
          }
        }
      }

      for (const player of allPlayersSet.values()) {
        distancesByPlayerId.set(player.player_id, { ...player, distance: 0 });
      }

      if (timeRange.length > 1) {
        for (let i = 1; i < timeRange.length; i++) {
          const tPrev = timeRange[i - 1];
          const tCurr = timeRange[i];

          const playersPrev = topViewStore.getFrameAt(tPrev);
          const playersCurr = topViewStore.getFrameAt(tCurr);
          if (!playersPrev || !playersCurr) continue;

          // Build Map lookup for prev frame instead of O(n) .find() per player
          const prevMap = new Map();
          for (const p of playersPrev) prevMap.set(p[0], p);

          for (const currPlayer of playersCurr) {
            if (currPlayer[1] === 0) continue;

            const prevPlayer = prevMap.get(currPlayer[0]);
            if (!prevPlayer) continue;
            if (!isInAnyZone(currPlayer[3], currPlayer[4], zones)) continue;

            if (
              (visualizationStore.showAggregatedFirst && currPlayer[2] !== 1) ||
              (visualizationStore.showAggregatedSecond && currPlayer[2] !== 2)
            ) {
              continue;
            }

            const dx = (currPlayer[3] - prevPlayer[3]) * playerStore.video.field_length;
            const dy = (currPlayer[4] - prevPlayer[4]) * playerStore.video.field_width;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (!distancesByPlayerId.has(currPlayer[0])) {
              distancesByPlayerId.set(currPlayer[0], {
                player_id: currPlayer[0],
                team_id: currPlayer[1],
                distance: 0,
              });
            }

            distancesByPlayerId.get(currPlayer[0]).distance += dist;
          }
        }
      }

      return Array.from(distancesByPlayerId.values())
        .map((item) => ({ ...item, distance: parseFloat(item.distance.toFixed(1)) }))
        .filter((p) => selectedPlayerIds.has(p.player_id))
        .sort((a, b) => a.player_id - b.player_id);
    }

    const selectedTimeRange = ref({
      start: 0,
      end: 0,
    });
    const minTimeGap = () => (1000 / playerStore.videoFPS) * 10;

    // Use cached maxTime from topViewStore's pre-sorted frame keys
    const maxFrameTime = computed(() => {
      const keys = topViewStore.sortedFrameKeys;
      return keys.length > 0 ? keys[keys.length - 1] : 0;
    });

    const _setSelectedTimeRangeStart = (time) => {
      const gap = minTimeGap();
      const max = maxFrameTime.value;

      let start = Math.max(0, Math.min(time, max - gap));
      selectedTimeRange.value.start = start;

      if (selectedTimeRange.value.end < start + gap) {
        selectedTimeRange.value.end = Math.min(start + gap, max);
      }
    };
    const setSelectedTimeRangeStart = throttle(_setSelectedTimeRangeStart, 30);

    const _setSelectedTimeRangeEnd = (time) => {
      const gap = minTimeGap();
      const max = maxFrameTime.value;

      let end = Math.min(max, Math.max(time, gap));
      selectedTimeRange.value.end = end;

      if (selectedTimeRange.value.start > end - gap) {
        selectedTimeRange.value.start = Math.max(end - gap, 0);
      }
    };
    const setSelectedTimeRangeEnd = throttle(_setSelectedTimeRangeEnd, 30);

    function setTimeRangeToFullMatch() {
      const keys = topViewStore.sortedFrameKeys;
      if (keys.length > 0) {
        selectedTimeRange.value = { start: keys[0], end: keys[keys.length - 1] };
      }
    }

    async function _restoreManual() {
      const id = positionDataId.value;
      if (!id) return;
      // positionDataList itself isn't persisted (it's just an index of what's
      // available, cheap to refetch) — loadPositionData() looks the id up in
      // it, so make sure it's populated before relying on a persisted id that
      // may otherwise still be empty this early after a reload.
      if (positionDataList.value.length === 0) {
        await loadPositionDataList();
      }
      await loadPositionData(id);
      await visualizationStore.loadKpiData(id);
    }

    // Mirrors ModalPositionDataSelect.vue's confirmSelection for the
    // bytetrack/object_tracker branch, using the plugin run ids persisted on
    // bboxesStore/topViewStore (see their `persist` options) instead of
    // whatever the modal's own v-models held — those aren't persisted, the
    // modal isn't even open across a reload. Deliberately does not touch
    // selectedTimeRange (unlike confirmSelection): that's already persisted
    // with whatever range was selected last, and re-deriving "full match"
    // here would silently discard it on every reload.
    async function _restoreTracker() {
      const trackerPluginId = bboxesStore.bboxPluginRunId;
      const calibrationAssetId = calibrationAssetStore.calibrationAssetId;
      if (!trackerPluginId || !calibrationAssetId) return;

      // Snapshot before the reload below -- transformBBoxToPositionDataTopView treats any
      // full (re)load of the tracker run as fresh and resets both of these to null (it can't
      // tell "just restoring after a browser refresh" apart from "a genuinely new tracker run
      // was picked"), so reading topViewStore.teamClusteringRunId/reidRunId *after* that call
      // would always see null and skip redoing the merges below.
      const teamClusteringRunId = topViewStore.teamClusteringRunId;
      const reidRunId = topViewStore.reidRunId;

      // calibrationAssetsList (unlike positionDataList) isn't fetched anywhere
      // by the time AnalysisView.vue calls restoreFromCache on mount — normally
      // ModalPositionDataSelect.vue's own mount populates it well before the
      // user can click confirm, but that modal never opens on a reload.
      // transformBBoxToPositionDataTopView -> loadCalibrationAsset does a
      // synchronous .find() on it, so without this it throws on the still-
      // default `{}`.
      await calibrationAssetStore.loadCalibrationAssetsList();
      await topViewStore.transformBBoxToPositionDataTopView(calibrationAssetId, trackerPluginId);
      if (bboxesStore.bboxBallPluginRunId) {
        await topViewStore.mergeBallTracking(calibrationAssetId, bboxesStore.bboxBallPluginRunId);
      }
      if (teamClusteringRunId) {
        await topViewStore.mergeTeamAssignment(teamClusteringRunId);
      }
      if (reidRunId) {
        await topViewStore.mergeReid(reidRunId);
      }
      await visualizationStore.loadKpiData(trackerPluginId);
    }

    /**
     * Clears the currently selected/loaded position data and everything derived from it -- the
     * topView pitch data, the bbox overlay + tracker-run ids, KPI data -- without touching
     * anything else (calibration mode, pitch grid/zones, event data stay as they are, unlike a
     * full AnalysisView unmount). Used by the "Position data" menu on TopView/VideoPlayer/
     * Heatmap/KPI cards so their empty state (PositionDataMenu) comes back and the user can
     * create/upload/select something new right there, without navigating back to VideoView.
     */
    function resetPositionData() {
      positionDataId.value = null;
      positionDataMode.value = null;
      selectedTimeRange.value = { start: 0, end: 0 };
      topViewStore.setPositionData(null, {});
      bboxesStore.bboxDataInterpolated = {};
      // Also clear the persisted tracker-run ids -- otherwise a later restoreFromCache (e.g. a
      // reload right after this) would try to restore the just-cleared selection right back.
      bboxesStore.bboxPluginRunId = 0;
      bboxesStore.bboxBallPluginRunId = null;
      topViewStore.teamClusteringRunId = null;
      topViewStore.reidRunId = null;
      visualizationStore.resetKpiData();
    }

    /**
     * Restore whichever position-data source was active before a reload,
     * using positionDataMode plus the source-specific ids persisted on this
     * store / bboxesStore / calibrationAssetStore / topViewStore (see each
     * store's `persist` option) — a reload never re-fetches everything, just
     * the one previously-selected dataset.
     */
    async function restoreFromCache() {
      if (!positionDataMode.value) return;
      if (topViewStore.sortedFrameKeys.length > 0) return;
      isRestoringPosData.value = true;
      try {
        if (positionDataMode.value === "manual") {
          await _restoreManual();
        } else {
          await _restoreTracker();
        }
      } finally {
        isRestoringPosData.value = false;
      }
    }

    return {
      positionDataList,
      positionDataId,
      positionDataMode,
      positionDataUploadSuccess,
      positionDataRenameSuccess,
      positionDataDeleteSuccess,
      loadPositionDataList,
      loadPositionData,
      uploadPositionData,
      renamePositionData,
      deletePositionData,
      isUploading,
      progress,
      provider,
      calculateRunningDistances,
      selectedTimeRange,
      setSelectedTimeRangeStart,
      setSelectedTimeRangeEnd,
      resetPositionData,
      restoreFromCache,
      isRestoringPosData,
    };
  },
  {
    persist: {
      pick: ["positionDataId", "positionDataMode", "selectedTimeRange"],
      storage: sessionStorage,
    },
  }
);
