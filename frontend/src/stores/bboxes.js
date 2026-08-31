import { ref } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useTopViewStore } from "@/stores/top_view";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

export const useBboxesStore = defineStore(
  "bboxes",
  () => {
    const playerStore = usePlayerStore();
    const pluginRunStore = usePluginRunStore();
    const pluginRunResultStore = usePluginRunResultStore();
    const topViewStore = useTopViewStore();
    const calibrationAssetStore = useCalibrationAssetStore();

    const bboxDataActive = ref({});
    const bboxMetaData = ref(null);
    const bboxDataInterpolated = ref({});
    const bboxDataTopView = ref({});
    const bboxDataLoaded = ref(false);

    const bboxPluginRunId = ref(0);

    // Separately-run ball-tracking result (no tracker, ball class only), merged into
    // bboxDataInterpolated/positionDataTopView by topViewStore.mergeBallTracking. Tracked
    // here so edits/deletes of a ball bbox can be routed to the correct plugin run instead
    // of the player run's (see updateBboxData/deleteBboxData below).
    const bboxBallDataActive = ref(null);
    const bboxBallMetaData = ref(null);
    const bboxBallPluginRunId = ref(null);

    // Raw osnet_reid mapping ({frame_time: {old_track_id: new_reid_id}}), set by
    // topViewStore.mergeReid once a ReID run is merged. b[0] in bboxDataActive then shows the
    // new reid id, but the backend's stored BboxesData for bboxPluginRunId still only knows the
    // original track_id -- translatePlayerId (below) reverses the swap for a given frame before
    // edits/deletes are sent, so editing continues to work without any backend changes.
    const bboxReidMapping = ref(null);

    const isLoading = ref(false);

    const loadBboxData = async (pluginRunId) => {
      let hasValidData = false;
      bboxPluginRunId.value = pluginRunId;

      try {
        const _bboxData = await Promise.all(
          pluginRunStore
            .forVideo(playerStore.videoId)
            .filter(
              (e) =>
                ["bytetrack", "object_tracker"].includes(e.type) &&
                e.status === "DONE" &&
                e.id === pluginRunId
            )
            .map(async (e) => ({
              ...e,
              results: await pluginRunResultStore.forPluginRunWithData(e.id, playerStore.videoId),
            }))
        );

        if (!_bboxData.length || !_bboxData[0]?.results?.length) {
          return [];
        }

        hasValidData = true;

        bboxDataActive.value = _bboxData[0]?.results[0]?.data?.bboxes;
        bboxMetaData.value = _bboxData[0]?.results[0]?.data?.meta_data ?? null;
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
      const _bboxDatainterpolated = [];

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
              _bboxDatainterpolated.push({
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
            _bboxDatainterpolated.push({ ...bbox, image_id: frame, time: frame / VideoFPS });
          });
        }
      }

      return _bboxDatainterpolated;
    }

    // Once a ReID run is merged (bboxReidMapping set), the player_id shown/edited in the UI is
    // the new reid id. Single-box edits (bbox tab) are translated back to the original
    // track_id for the affected frame so the existing edit endpoint (which only knows the
    // object_tracker run's original ids) still finds the right row. Bulk "apply to all
    // player id" edits are intentionally left untranslated -- a single reid identity can map
    // to several different original track_ids over time, so a global rename is ambiguous; that
    // mode is hidden in the UI whenever a ReID merge is active (see BboxIdentityPanel.vue).
    const translatePlayerId = (bboxData) => {
      if (!bboxReidMapping.value || bboxData.applyAllPlayerId || bboxData.applyAllTeamId) {
        return bboxData;
      }
      const [frameKey] = String(bboxData.bboxId).split("-");
      const frameMapping = bboxReidMapping.value[frameKey];
      if (!frameMapping) return bboxData;

      const originalId = Object.entries(frameMapping).find(
        ([, newId]) => newId === bboxData.playerId
      )?.[0];
      if (originalId === undefined) return bboxData;

      return {
        ...bboxData,
        playerId: Number(originalId),
        bboxId: `${frameKey}-${originalId}`,
      };
    };

    const updateBboxData = async (bboxDataAsDisplayed) => {
      if (isLoading.value) return;
      const bboxData = translatePlayerId(bboxDataAsDisplayed);
      isLoading.value = true;
      const params = ref({});

      if (!bboxData.applyAllPlayerId && !bboxData.applyAllTeamId) {
        params.value = {
          object_tracker_run_id: bboxData.bytetrackRunId,
          bbox_id: bboxData.bboxId,
          player_id: bboxData.playerId,
          new_player_id: bboxData.newPlayerId,
          team_id: bboxData.teamId?.id ?? bboxData.teamId,
          new_team_id: bboxData.newTeamId,
        };
      } else if (bboxData.applyAllPlayerId) {
        params.value = {
          object_tracker_run_id: bboxData.bytetrackRunId,
          player_id: bboxData.playerId,
          new_player_id: bboxData.newPlayerId,
          team_id: bboxData.teamId?.id ?? bboxData.teamId,
          new_team_id: bboxData.newTeamId,
          update_all_player_id: bboxData.applyAllPlayerId,
        };
      } else if (bboxData.applyAllTeamId) {
        params.value = {
          object_tracker_run_id: bboxData.bytetrackRunId,
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
        if (res.data.status === "ok") {
          // Route the refresh to whichever plugin run was actually edited, so the
          // merged view (VideoPlayer overlay + TopView) reflects the change without
          // dropping the other run's data.
          if (bboxData.bytetrackRunId === bboxBallPluginRunId.value) {
            topViewStore.refreshBallBboxData(res.data.entry.bboxes, res.data.entry.meta_data);
          } else if (topViewStore.teamClusteringRunId || topViewStore.reidRunId) {
            // A team_clustering/reid merge is layered on top of this run client-side only
            // (see topViewStore.mergeTeamAssignment/mergeReid) -- the server has no notion
            // of it, so res.data.entry.bboxes is still the run's raw, un-merged data.
            // Replacing bboxDataActive with it wholesale would drop the merge for every
            // row except the one just edited. Patch the same edit directly onto the
            // already-merged copy instead, using the as-displayed (pre-translation)
            // request so ids line up with what's stored in bboxDataActive.
            topViewStore.applyLocalBboxEdit(bboxDataAsDisplayed);
          } else {
            bboxMetaData.value = res.data.entry.meta_data ?? null;
            topViewStore.transformBBoxToPositionDataTopView(
              calibrationAssetStore.calibrationAssetId,
              bboxPluginRunId.value,
              res.data.entry.bboxes
            );
          }

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

    const deleteBboxData = async (bboxDataAsDisplayed) => {
      if (isLoading.value) return;
      const bboxData = translatePlayerId(bboxDataAsDisplayed);
      isLoading.value = true;
      const params = ref({});

      if (!bboxData.applyAllPlayerId && !bboxData.applyAllTeamId) {
        params.value = {
          object_tracker_run_id: bboxData.bytetrackRunId,
          bbox_id: bboxData.bboxId,
        };
      } else if (bboxData.applyAllPlayerId) {
        params.value = {
          object_tracker_run_id: bboxData.bytetrackRunId,
          player_id: bboxData.playerId,
          delete_all_player_id: bboxData.applyAllPlayerId,
        };
      } else if (bboxData.applyAllTeamId) {
        params.value = {
          object_tracker_run_id: bboxData.bytetrackRunId,
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
          if (bboxData.bytetrackRunId === bboxBallPluginRunId.value) {
            topViewStore.refreshBallBboxData(res.data.entry.bboxes, res.data.entry.meta_data);
          } else if (topViewStore.teamClusteringRunId || topViewStore.reidRunId) {
            // See the matching branch in updateBboxData above for why the merged copy is
            // patched locally instead of being replaced by the server's raw response.
            topViewStore.applyLocalBboxDelete(bboxDataAsDisplayed);
          } else {
            bboxMetaData.value = res.data.entry.meta_data ?? null;
            topViewStore.transformBBoxToPositionDataTopView(
              calibrationAssetStore.calibrationAssetId,
              bboxPluginRunId.value,
              res.data.entry.bboxes
            );
          }

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

    // Persists a full, client-computed bboxes array as the new data for a tracker run --
    // used by topViewStore.mergeTeamAssignment to permanently bake a team_clustering merge
    // into the run itself (see that function's comment for why: team_clustering writes into
    // its own separate plugin run and never touches the tracker's stored data on its own).
    const replaceBboxData = async (objectTrackerRunId, bboxesJson) => {
      const res = await axios.post(`${config.API_LOCATION}/position_data/bboxes/replace`, {
        object_tracker_run_id: objectTrackerRunId,
        bboxes: bboxesJson,
      });
      return res.data;
    };

    const showBoundingBox = ref(false);
    const viewBoundingBox = () => {
      showBoundingBox.value = !showBoundingBox.value;
    };

    // Player-id label on the video overlay's bounding boxes. Deliberately its own flag
    // rather than reusing topViewStore.showPlayerId — the video and top-view cards render
    // fully separate entity overlays now, so showing ids in one shouldn't force them on in
    // the other (see viewBoundingBox above, which already only ever affected this overlay).
    // Defaults to on (unlike showBoundingBox/topViewStore.showPlayerId) since the id label
    // is the main thing that makes the box overlay useful once it's switched on.
    const showPlayerId = ref(true);
    const viewPlayerId = () => {
      showPlayerId.value = !showPlayerId.value;
    };

    // Which entity kinds render on the video overlay. Mirrors topViewStore's
    // visibleEntityKinds/toggleEntityKind (same defaults), but kept as its own state for the
    // same reason as showPlayerId above.
    const visibleEntityKinds = ref({ player: true, ref: false, ball: true, rest: false });
    const toggleEntityKind = (kind) => {
      visibleEntityKinds.value = {
        ...visibleEntityKinds.value,
        [kind]: !visibleEntityKinds.value[kind],
      };
    };

    const bboxDataUpdateSuccess = ref(false);
    const bboxDataSingleUpdateSuccess = ref(false);
    const bboxDataDeleteSuccess = ref(false);
    const bboxDataSingleDeleteSuccess = ref(false);

    return {
      loadBboxData,
      updateBboxData,
      deleteBboxData,
      replaceBboxData,
      interpolateBboxData,
      bboxDataActive,
      bboxMetaData,
      bboxDataLoaded,
      bboxDataInterpolated,
      bboxPluginRunId,
      bboxBallDataActive,
      bboxBallMetaData,
      bboxBallPluginRunId,
      bboxReidMapping,
      bboxDataTopView,
      showBoundingBox,
      viewBoundingBox,
      showPlayerId,
      viewPlayerId,
      visibleEntityKinds,
      toggleEntityKind,
      bboxDataUpdateSuccess,
      bboxDataSingleUpdateSuccess,
      bboxDataDeleteSuccess,
      bboxDataSingleDeleteSuccess,
    };
  },
  {
    // Only the ids needed to redo the tracker load on a reload (see
    // position_data.js's restoreFromCache) — the heavy bbox/meta data itself
    // is re-fetched from the backend, same as manual position data.
    persist: {
      pick: ["bboxPluginRunId", "bboxBallPluginRunId"],
      storage: sessionStorage,
    },
  }
);
