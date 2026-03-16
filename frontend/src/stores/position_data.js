import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { throttle } from "lodash";
import axios from "../plugins/axios";
import config from "../../app.config";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useTopViewStore } from "./top_view";
import { useBboxesStore } from "./bboxes";
import { useVisualizationStore } from "@/stores/visualization";
import { usePosdataWorkerStore } from "@/stores/posdata_worker";

export const usePositionDataStore = defineStore(
  "position_data",
  () => {
    const playerStore = usePlayerStore();
    const pluginRunStore = usePluginRunStore();
    const pluginRunResultStore = usePluginRunResultStore();
    const topViewStore = useTopViewStore();
    const bboxesStore = useBboxesStore();
    const visualizationStore = useVisualizationStore();

    const positionDataList = ref([]);
    const positionDataId = ref(null);
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
        topViewStore.positionDataTopView = cached.posData;
        topViewStore.metaDataTopView = cached.metaData;
        setTimeRangeToFullMatch();
        return;
      }

      // 2. Try existing plugin run results (already in memory from fetchForVideo)
      const _positionData = pluginRunStore
        .forVideo(playerStore.videoId)
        .filter((e) => e.type === "posdata_convert" && e.status === "DONE")
        .map((e) => {
          const results = pluginRunResultStore.forPluginRun(e.id);
          return { ...e, results: JSON.parse(JSON.stringify(results)) };
        })
        .filter((e) => e.results?.[0]?.data?.tracking_data_id === id);

      const posData = _positionData[0]?.results[0]?.data?.pos_data;
      const metaData = _positionData[0]?.results[0]?.data?.meta_data;

      if (posData) {
        topViewStore.positionDataTopView = posData;
        topViewStore.metaDataTopView = metaData || {};
        // Store in in-memory cache for future accesses
        workerStore.cacheData(id, posData, metaData || {});
        setTimeRangeToFullMatch();
        return;
      }

      // 3. Chunk-load from backend (progressive, with progress bar)
      const result = await workerStore.loadChunked(id, playerStore.videoId);
      if (result) {
        topViewStore.positionDataTopView = result.posData;
        topViewStore.metaDataTopView = result.metaData;
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
            topViewStore.positionDataTopView = {};
            topViewStore.metaDataTopView = {};
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
        if (x >= z.x0 && x <= z.x1 && y >= z.y0 && y <= z.y1) return true;
      }
      return false;
    }

    function calculateRunningDistances(selectedPlayerIds, startFrame, endFrame, zones = []) {
      const distancesByPlayerId = new Map();

      const allTimes = Object.keys(topViewStore.positionDataTopView).map(Number);

      const timeRange = allTimes.filter((t) => t >= startFrame && t <= endFrame);

      const allPlayersSet = new Map();

      for (const frame of allTimes) {
        const players = topViewStore.positionDataTopView[frame];
        if (!players) continue;
        for (const p of players) {
          if (p[1] === 1) continue;
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

          const playersPrev = topViewStore.positionDataTopView[tPrev];
          const playersCurr = topViewStore.positionDataTopView[tCurr];
          if (!playersPrev || !playersCurr) continue;

          for (const currPlayer of playersCurr) {
            if (currPlayer[1] === 1) continue;

            const prevPlayer = playersPrev.find((p) => p[0] === currPlayer[0]);
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

    /**
     * Restore posData after navigation. Checks in-memory cache first,
     * then falls back to a full reload from the backend.
     */
    async function restoreFromCache() {
      const id = positionDataId.value;
      if (!id) return;
      if (Object.keys(topViewStore.positionDataTopView).length > 0) return;
      isRestoringPosData.value = true;
      try {
        await loadPositionData(id);
      } finally {
        isRestoringPosData.value = false;
      }
    }

    return {
      positionDataList,
      positionDataId,
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
      restoreFromCache,
      isRestoringPosData,
    };
  },
  {
    persist: {
      pick: ["positionDataId", "selectedTimeRange"],
      storage: sessionStorage,
    },
  }
);
