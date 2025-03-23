import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export const useBBoxesStore = defineStore("bboxes", () => {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();

  // const bboxData = computed(() => {
  //   let _bboxData = pluginRunStore
  //     .forVideo(playerStore.videoId)
  //     .filter((e) => e.type == "bytetrack" && e.status == "DONE")
  //     .slice(-1)
  //     .map((e) => {
  //       e.results = pluginRunResultStore.forPluginRun(e.id);
  //       return e;
  //     });
  //   return _bboxData?.[0]?.results?.[0]?.data?.bboxes;
  // });

  const bboxDataLoaded = ref(false);
  const bboxData = computed(() => {
    let _bboxData;
    let hasValidData = false;

    try {
      _bboxData = pluginRunStore
        .forVideo(playerStore.videoId)
        .filter((e) => e.type === "bytetrack" && e.status === "DONE")
        .slice(-1)
        .map((e) => {
          e.results = pluginRunResultStore.forPluginRun(e.id);
          return e;
        });

      if (!_bboxData.length || !_bboxData[0]?.results?.length) {
        console.error("Bytetrack: Not run or not finished yet");
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
  });

  const showBoundingBox = ref(false);
  const viewBoundingBox = () => {
    showBoundingBox.value = !showBoundingBox.value;
  };

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

  return {
    bboxData,
    bboxDataLoaded,
    showBoundingBox,
    viewBoundingBox,
    showSpaceControl,
    viewSpaceControl,
    showEffectivePlayingSpace,
    viewEffectivePlayingSpace,
    positionsNested,
    positionsFlat,
  };
});
