import { ref, computed, watch } from "vue";
import { defineStore } from "pinia";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useCalibrationAssetStore } from "./calibration_asset";

export const useBboxesStore = defineStore("bboxes", () => {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();
  const calibrationAssetStore = useCalibrationAssetStore();

  const bboxData = ref({});
  const bboxDataInterpolated = ref({});
  const bboxDataTopView = ref({});
  const bboxDataLoaded = ref(false);

  const bboxPluginRun = ref(0);

  const setBboxData = (pluginRun) => {
    let _bboxData;
    let hasValidData = false;

    try {
      _bboxData = pluginRunStore
        .forVideo(playerStore.videoId)
        .filter((e) => e.type === "bytetrack" && e.status === "DONE")
        .slice(pluginRun)
        .map((e) => {
          e.results = pluginRunResultStore.forPluginRun(e.id);
          return e;
        });

      if (!_bboxData.length || !_bboxData[0]?.results?.length) {
        return [];
      }

      hasValidData = true;
      return _bboxData[0]?.results[0]?.data?.bboxes || [];
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
          const next = nextBboxes.find((b) => b.ref_id === prev.ref_id);

          if (next) {
            const alpha = srcFrame - prevFrame;
            bboxDatainterpolated.push({
              x: prev.x + (next.x - prev.x) * alpha,
              y: prev.y + (next.y - prev.y) * alpha,
              w: prev.w + (next.w - prev.w) * alpha,
              h: prev.h + (next.h - prev.h) * alpha,
              team: prev.team,
              image_id: frame,
              time: frame / VideoFPS,
              ref_id: prev.ref_id,
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

  const setbboxDataTopView = (bboxData) => {
    return bboxData.map((bbox) => {
      const point = {
        x: bbox.x + bbox.w / 2,
        y: bbox.y + bbox.h,
      };
      if (calibrationAssetStore.calibrationMatrix) {
        const transformed = calibrationAssetStore.applyHomography(
          calibrationAssetStore.calibrationMatrix,
          point
        );
        return {
          ...bbox,
          new_x: transformed.x,
          new_y: transformed.y,
        };
      }
      return {
        ...bbox,
        new_x: point.x,
        new_y: point.y,
      };
    });
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

  const showBoundingBox = ref(false);
  const viewBoundingBox = () => {
    showBoundingBox.value = !showBoundingBox.value;
  };

  const posDataUploadSuccess = ref(false);

  return {
    bboxData,
    setBboxData,
    bboxDataLoaded,
    showBoundingBox,
    viewBoundingBox,
    showSpaceControl,
    viewSpaceControl,
    showEffectivePlayingSpace,
    viewEffectivePlayingSpace,
    interpolateBboxData,
    bboxDataInterpolated,
    bboxPluginRun,
    bboxDataTopView,
    setbboxDataTopView,
    posDataUploadSuccess,
  };
});
