import { ref } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useTopViewStore } from "@/stores/top_view";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

export const useBboxesStore = defineStore("bboxes", () => {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();
  const topViewStore = useTopViewStore();
  const calibrationAssetStore = useCalibrationAssetStore();

  const bboxDataActive = ref({});
  const bboxDataInterpolated = ref({});
  const bboxDataTopView = ref({});
  const bboxDataLoaded = ref(false);

  const bboxPluginRunId = ref(0);

  const isLoading = ref(false);

  const loadBboxData = async (pluginRunId) => {
    let hasValidData = false;
    bboxPluginRunId.value = pluginRunId;

    try {
      const _bboxData = pluginRunStore
        .forVideo(playerStore.videoId)
        .filter((e) => e.type === "bytetrack" && e.status === "DONE" && e.id === pluginRunId)
        .map((e) => {
          e.results = pluginRunResultStore.forPluginRun(e.id);
          return e;
        });

      if (!_bboxData.length || !_bboxData[0]?.results?.length) {
        return [];
      }

      hasValidData = true;

      bboxDataActive.value = _bboxData[0]?.results[0]?.data?.bboxes;
    } finally {
      if (hasValidData) {
        bboxDataLoaded.value = true;
      } else {
        bboxDataLoaded.value = false;
      }
    }
  };

  function interpolateBboxData(bboxData, VideoFPS, bboxDataFPS) {
    const factor = VideoFPS / bboxDataFPS;
    if (factor == 1) return bboxData;
    const bboxDatainterpolated = [];

    // Group bboxes by image_id
    const bboxMap = new Map();
    bboxData.forEach((bbox) => {
      if (!bboxMap.has(bbox.image_id)) {
        bboxMap.set(bbox.image_id, []);
      }
      bboxMap.get(bbox.image_id).push(bbox);
    });

    // Determine maximum frame
    const maxFrame = Math.max(...bboxMap.keys());

    for (let frame = 0; frame <= maxFrame * factor; frame++) {
      const srcFrame = frame / factor;
      const prevFrame = Math.floor(srcFrame);
      const nextFrame = Math.ceil(srcFrame);

      if (bboxMap.has(prevFrame) && bboxMap.has(nextFrame) && prevFrame !== nextFrame) {
        // Interpolation between two known frames
        const prevBboxes = bboxMap.get(prevFrame);
        const nextBboxes = bboxMap.get(nextFrame);

        prevBboxes.forEach((prev, index) => {
          const next = nextBboxes.find((b) => b.player_id === prev.player_id);

          if (next) {
            const alpha = srcFrame - prevFrame;
            bboxDatainterpolated.push({
              x: prev.x + (next.x - prev.x) * alpha,
              y: prev.y + (next.y - prev.y) * alpha,
              w: prev.w + (next.w - prev.w) * alpha,
              h: prev.h + (next.h - prev.h) * alpha,
              team_id: prev.team_id,
              image_id: frame,
              time: frame / VideoFPS,
              player_id: prev.player_id,
              det_score: prev.det_score + (next.det_score - prev.det_score) * alpha,
            });
          }
        });
      } else if (bboxMap.has(prevFrame)) {
        bboxMap.get(prevFrame).forEach((bbox) => {
          bboxDatainterpolated.push({ ...bbox, image_id: frame, time: frame / VideoFPS });
        });
      }
    }

    return bboxDatainterpolated;
  }

  const updateBboxData = async (bboxData) => {
    if (isLoading.value) return;
    isLoading.value = true;
    const params = ref({});

    if (!bboxData.applyAllPlayerId && !bboxData.applyAllTeamId) {
      params.value = {
        bytetrack_run_id: bboxData.bytetrackRunId,
        bbox_id: bboxData.bboxId,
        player_id: bboxData.playerId,
        new_player_id: bboxData.newPlayerId,
        team_id: bboxData.teamId?.id ?? bboxData.teamId,
        new_team_id: bboxData.newTeamId,
      };
    } else if (bboxData.applyAllPlayerId) {
      params.value = {
        bytetrack_run_id: bboxData.bytetrackRunId,
        player_id: bboxData.playerId,
        new_player_id: bboxData.newPlayerId,
        team_id: bboxData.teamId?.id ?? bboxData.teamId,
        new_team_id: bboxData.newTeamId,
        update_all_player_id: bboxData.applyAllPlayerId,
      };
    } else if (bboxData.applyAllTeamId) {
      params.value = {
        bytetrack_run_id: bboxData.bytetrackRunId,
        team_id: bboxData.teamId?.id ?? bboxData.teamId,
        new_team_id: bboxData.newTeamId,
        update_all_team_id: bboxData.applyAllTeamId,
      };
    }

    try {
      const res = await axios.post(
        `${config.API_LOCATION}/position_data/bboxes/edit`,
        params.value
      );
      console.log("res", res);
      if (res.data.status === "ok") {
        topViewStore.transformBBoxToPositionDataTopView(
          calibrationAssetStore.calibrationAssetId,
          bboxPluginRunId.value,
          res.data.entry.bboxes
        );

        if (bboxData.applyAllPlayerId || bboxData.applyAllTeamId) {
          bboxDataUpdateSuccess.value = true;
        } else {
          bboxDataSingleUpdateSuccess.value = true;
        }
      }
    } finally {
      isLoading.value = false;
    }
  };

  const deleteBboxData = async (bboxData) => {
    if (isLoading.value) return;
    isLoading.value = true;
    const params = ref({});

    if (!bboxData.applyAllPlayerId && !bboxData.applyAllTeamId) {
      params.value = {
        bytetrack_run_id: bboxData.bytetrackRunId,
        bbox_id: bboxData.bboxId,
      };
    } else if (bboxData.applyAllPlayerId) {
      params.value = {
        bytetrack_run_id: bboxData.bytetrackRunId,
        player_id: bboxData.playerId,
        delete_all_player_id: bboxData.applyAllPlayerId,
      };
    } else if (bboxData.applyAllTeamId) {
      params.value = {
        bytetrack_run_id: bboxData.bytetrackRunId,
        team_id: bboxData.teamId?.id ?? bboxData.teamId,
        delete_all_team_id: bboxData.applyAllTeamId,
      };
    }

    try {
      const res = await axios.post(
        `${config.API_LOCATION}/position_data/bboxes/delete`,
        params.value
      );
      if (res.data.status === "ok") {
        topViewStore.transformBBoxToPositionDataTopView(
          calibrationAssetStore.calibrationAssetId,
          bboxPluginRunId.value,
          res.data.entry.bboxes
        );

        if (bboxData.applyAllPlayerId || bboxData.applyAllTeamId) {
          bboxDataDeleteSuccess.value = true;
        } else {
          bboxDataSingleDeleteSuccess.value = true;
        }
      }
    } finally {
      isLoading.value = false;
    }
  };

  const showBoundingBox = ref(false);
  const viewBoundingBox = () => {
    showBoundingBox.value = !showBoundingBox.value;
  };

  const bboxDataUpdateSuccess = ref(false);
  const bboxDataSingleUpdateSuccess = ref(false);
  const bboxDataDeleteSuccess = ref(false);
  const bboxDataSingleDeleteSuccess = ref(false);

  return {
    loadBboxData,
    updateBboxData,
    deleteBboxData,
    interpolateBboxData,
    bboxDataActive,
    bboxDataLoaded,
    bboxDataInterpolated,
    bboxPluginRunId,
    bboxDataTopView,
    showBoundingBox,
    viewBoundingBox,
    bboxDataUpdateSuccess,
    bboxDataSingleUpdateSuccess,
    bboxDataDeleteSuccess,
    bboxDataSingleDeleteSuccess,
  };
});
