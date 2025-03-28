import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export const useBboxesStore = defineStore("bboxes", () => {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();

  const bboxData = ref([]);
  const bboxDataInterpolated = ref([]);
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

  function interpolateBoundingBoxes(bboxData, VideoFPS, bboxDataFPS) {
    const factor = VideoFPS / bboxDataFPS;
    const interpolatedData = [];

    // Group bboxes by `image_id`
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
          const next = nextBboxes.find((b) => b.ref_id === prev.ref_id); // Find same ID

          if (next) {
            const alpha = srcFrame - prevFrame; // Interpolation factor between 0 and 1
            interpolatedData.push({
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
        // If there is no next frame, use the previous value
        bboxMap.get(prevFrame).forEach((bbox) => {
          interpolatedData.push({ ...bbox, image_id: frame, time: frame / VideoFPS });
        });
      }
    }

    return interpolatedData;
  }

  const positionsNested = ref(
    Array.from({ length: 100 }, () =>
      Array.from({ length: 20 }, (_, playerIndex) => {
        const isTeamA = playerIndex < 10;

        return {
          bbox_top: Math.random() * 0.8 + 0.1, // x
          bbox_left: Math.random() * 0.6 + (isTeamA ? 0.1 : 0.3), // y
          bbox_width: 0.05, // w
          bbox_height: 0.1, // h
          team: isTeamA ? "blue" : "red", // will be in class BboxDataTeam
          image_id: 0, // image_id (= frame)
          time: 0, // image_id / fps
          ref_id: 1,
          det_score: 1.0,
        };
      })
    )
  );

  const positionsFlat = ref(
    Array.from({ length: 100 * 20 }, (_, index) => {
      const image_id = Math.floor(index / 20); // Frame (0-99)
      const ref_id = (index % 20) + 1; // Spieler-ID (1-20)
      const isTeamA = ref_id <= 10; // Team-Zuordnung

      return {
        y: Math.random() * 0.8 + 0.1,
        x: Math.random() * 0.6 + (isTeamA ? 0.1 : 0.3),
        w: 0.05,
        h: 0.1,
        team: isTeamA ? "blue" : "red",
        image_id: image_id,
        time: image_id / 1, // Angenommene FPS von 1
        ref_id: ref_id,
        det_score: 1.0, // Bbox-Wahrscheinlichkeit
      };
    })
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
    interpolateBoundingBoxes,
    bboxDataInterpolated,
    bboxPluginRun,
  };
});
