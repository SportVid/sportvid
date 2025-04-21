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

  const positionsFlat = ref([]);
  const positionsNested = ref([]);
  watch(
    () => playerStore.videoDuration,
    (newDuration) => {
      if (newDuration > 0) {
        positionsFlat.value = Array.from(
          { length: newDuration * playerStore.videoFPS * 20 },
          (_, index) => {
            const image_id = Math.floor(index / 20);
            const ref_id = (index % 20) + 1;
            const isTeamA = ref_id <= 10;

            const x = Math.random() * 0.6 + (isTeamA ? 0.1 : 0.3);
            const y = Math.random() * 0.8 + 0.1;
            const w = 0.05;
            const h = 0.1;

            return {
              x: x,
              y: y,
              w: w,
              h: h,
              new_x: x + w / 2,
              new_y: y + h,
              team: isTeamA ? "blue" : "red",
              image_id: image_id,
              time: image_id / playerStore.videoFPS,
              ref_id: ref_id,
              det_score: 1.0,
            };
          }
        );
        positionsNested.value = Array.from(
          { length: newDuration * playerStore.videoFPS * 20 },
          (_, frameIndex) =>
            Array.from({ length: 20 }, (_, playerIndex) => {
              const isTeamA = playerIndex < 10;
              const x = Math.random() * 0.6 + (isTeamA ? 0.1 : 0.3);
              const y = Math.random() * 0.8 + 0.1;
              const w = 0.05;
              const h = 0.1;
              return {
                bbox_top: y,
                bbox_left: x,
                bbox_width: w,
                bbox_height: h,
                new_x: x + w / 2,
                new_y: y + h,
                team: isTeamA ? "blue" : "red",
                image_id: frameIndex,
                time: frameIndex / playerStore.videoFPS,
                ref_id: playerIndex,
                det_score: 1.0,
              };
            })
        );
      }
    }
  );

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
    positionsNested,
    positionsFlat,
    interpolateBboxData,
    bboxDataInterpolated,
    bboxPluginRun,
    bboxDataTopView,
    setbboxDataTopView,
  };
});
