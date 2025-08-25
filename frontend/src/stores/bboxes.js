import { ref } from "vue";
import { defineStore } from "pinia";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useTopViewStore } from "./top_view";

export const useBboxesStore = defineStore("bboxes", () => {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();
  const topViewStore = useTopViewStore();

  const bboxDataActive = ref({});
  const bboxDataInterpolated = ref({});
  const bboxDataTopView = ref({});
  const bboxDataLoaded = ref(false);

  const bboxPluginRunId = ref(0);

  const loadBboxData = (pluginRunId) => {
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
      // topViewStore.positionDataTopView = {
      //   0: [
      //     { pos_x: 0.45285255859549833, pos_y: 1.0432065609928973, player_id: 1, team_id: "None" },
      //     { pos_x: 0.4095171526402028, pos_y: 1.0441847099654447, player_id: 2, team_id: "None" },
      //     { pos_x: 0.4008530607134673, pos_y: 1.0488220057471758, player_id: 3, team_id: "None" },
      //     { pos_x: 0.5380372403756356, pos_y: 0.6981593840609488, player_id: 4, team_id: "None" },
      //     { pos_x: 0.44680095813270015, pos_y: 0.6285184907187099, player_id: 5, team_id: "None" },
      //     { pos_x: 0.5581394042998931, pos_y: 0.613133534848689, player_id: 6, team_id: "None" },
      //     { pos_x: 0.5568072860251395, pos_y: 0.4688643697498366, player_id: 7, team_id: "None" },
      //     { pos_x: 0.3656300156149409, pos_y: 1.0543413650538709, player_id: 8, team_id: "None" },
      //     { pos_x: 0.4461924959356261, pos_y: 0.5045449659830928, player_id: 9, team_id: "None" },
      //     { pos_x: 0.5040426385038732, pos_y: 0.4739950972301284, player_id: 10, team_id: "None" },
      //   ],
      // };
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

  const positionDataUploadSuccess = ref(false);

  return {
    loadBboxData,
    interpolateBboxData,
    bboxDataActive,
    bboxDataLoaded,
    bboxDataInterpolated,
    bboxPluginRunId,
    bboxDataTopView,
    positionDataUploadSuccess,
  };
});
