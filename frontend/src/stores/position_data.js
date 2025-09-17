import { ref } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useTopViewStore } from "./top_view";
import { useBboxesStore } from "./bboxes";
import { useVisualizationStore } from "@/stores/visualization";

export const usePositionDataStore = defineStore("position_data", () => {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();
  const topViewStore = useTopViewStore();
  const bboxesStore = useBboxesStore();
  const visualizationStore = useVisualizationStore();

  const positionDataList = ref([]);
  const positionDataId = ref(null);

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
      const res = await axios.get(`${config.API_LOCATION}/tracking_data/list`);
      if (res.data.status === "ok") {
        positionDataList.value = res.data.entries;
      }
    } catch (error) {
      console.error("Failed to list tracking data:", error);
    }
  };

  const loadPositionData = (id) => {
    const selectedPositionData = positionDataList.value.find((data) => data.id === id);
    if (selectedPositionData) {
      positionDataId.value = id;
      console.log("pos-data id", positionDataId.value);

      const _positionData = pluginRunStore
        .forVideo(playerStore.videoId)
        .filter((e) => e.type === "posdata_convert" && e.status === "DONE")
        .map((e) => {
          const results = pluginRunResultStore.forPluginRun(e.id);
          return { ...e, results: JSON.parse(JSON.stringify(results)) };
        })
        .filter((e) => e.results?.[0]?.data?.tracking_data_id === id);

      topViewStore.metaDataTopView = _positionData[0]?.results[0]?.data?.meta_data;
      topViewStore.positionDataTopView = _positionData[0]?.results[0]?.data?.pos_data;
      bboxesStore.bboxDataActive = {};
      bboxesStore.bboxDataInterpolated = {};
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
      }
    } catch (error) {
      console.error("Failed to delete position data:", error);
    } finally {
    }
  };

  function calculateRunningDistances(selectedPlayerIds, startFrame, endFrame) {
    const distancesByPlayerId = new Map();

    const allTimes = Object.keys(topViewStore.positionDataTopView).map(Number);

    const timeRange = allTimes.filter(
      (t) =>
        t >= startFrame &&
        t <= endFrame &&
        (!visualizationStore.showProgress || t <= playerStore.currentTime)
    );

    const allPlayersSet = new Map();

    for (const frame of allTimes) {
      const players = topViewStore.positionDataTopView[frame];
      if (!players) continue;
      for (const p of players) {
        if (p[1] === 1) continue; // Ball raus
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
      .map((item) => ({ ...item, distance: Number(item.distance.toFixed(2)) }))
      .filter((p) => selectedPlayerIds.has(p.player_id))
      .sort((a, b) => a.player_id - b.player_id);
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
  };
});
