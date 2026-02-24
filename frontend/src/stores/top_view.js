import { defineStore } from "pinia";
import { nextTick, ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useBboxesStore } from "@/stores/bboxes";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePlayerStore } from "@/stores/player";

export const useTopViewStore = defineStore(
  "top_view",
  () => {
    const bboxesStore = useBboxesStore();
    const calibrationAssetStore = useCalibrationAssetStore();
    const playerStore = usePlayerStore();

    const { t } = useI18n();

    const showItems = ref(false);

    const topViewSize = ref({ width: 0, height: 0, top: 0, left: 0 });
    const setTopViewSize = (size) => {
      topViewSize.value = size;
    };

    const currentAreaSize = ref("full");

    const currentSport = ref({
      title: t("sports.soccer"),
      areaImage: require("../assets/top-view/pitch_soccer_full.png"),
      areas: {
        full: {
          image: require("../assets/top-view/pitch_soccer_full.png"),
          templateCrop: { x: [0, 1], y: [0, 1] },
          widthRel: 2100 / 2260,
          heightRel: 1360 / 1519,
        },
        half: {
          image: require("../assets/top-view/pitch_soccer_half.png"),
          templateCrop: { x: [0, 0.5], y: [0, 1] },
          widthRel: 1050 / 1210,
          heightRel: 1360 / 1519,
        },
        penToPen: {
          image: require("../assets/top-view/pitch_soccer_pen_to_pen.png"),
          templateCrop: { x: [0.16, 0.84], y: [0, 1] },
          widthRel: 1440 / 1350,
          heightRel: 1360 / 1270,
        },
        doublePen: {
          image: require("../assets/top-view/pitch_soccer_double_pen.png"),
          templateCrop: { x: [0, 0.32], y: [0.18, 0.82] },
          widthRel: 660 / 820,
          heightRel: 806 / 966,
        },
      },
      widthRel: 2100 / 2260,
      heightRel: 1360 / 1519,
    });
    const sports = ref([
      {
        title: t("sports.soccer"),
        areaImage: require("../assets/top-view/pitch_soccer_full.png"),
        areas: {
          full: {
            image: require("../assets/top-view/pitch_soccer_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 2100 / 2260,
            heightRel: 1360 / 1519,
          },
          half: {
            image: require("../assets/top-view/pitch_soccer_half.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 1050 / 1210,
            heightRel: 1360 / 1519,
          },
          penToPen: {
            image: require("../assets/top-view/pitch_soccer_pen_to_pen.png"),
            templateCrop: { x: [0.1575, 0.8425], y: [0, 1] },
            widthRel: 1440 / 1600,
            heightRel: 1360 / 1519,
          },
          doublePen: {
            image: require("../assets/top-view/pitch_soccer_double_pen.png"),
            templateCrop: { x: [0, 0.315], y: [0.2025, 0.7975] },
            widthRel: 660 / 820,
            heightRel: 806 / 966,
          },
        },
      },
      {
        title: t("sports.handball"),
        areaImage: require("../assets/top-view/pitch_handball_full.png"),
        areas: {
          full: {
            image: require("../assets/top-view/pitch_handball_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 2428 / 2622,
            heightRel: 1216 / 1410,
          },
          half: {
            image: require("../assets/top-view/pitch_handball_full.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 2428 / 2622,
            heightRel: 1216 / 1410,
          },
        },
      },
      {
        title: t("sports.basketball"),
        areaImage: require("../assets/top-view/court_basketball_full.png"),
        areas: {
          full: {
            image: require("../assets/top-view/court_basketball_full.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 2278 / 2460,
            heightRel: 1322 / 1504,
          },
          half: {
            image: require("../assets/top-view/court_basketball_full.png"),
            templateCrop: { x: [0, 0.5], y: [0, 1] },
            widthRel: 2278 / 2460,
            heightRel: 1322 / 1504,
          },
        },
      },
      {
        title: t("sports.climbing"),
        areaImage: require("../assets/top-view/area_climbing.png"),
        areas: {
          full: {
            image: require("../assets/top-view/area_climbing.png"),
            templateCrop: { x: [0, 1], y: [0, 1] },
            widthRel: 1492 / 2800,
            heightRel: 1866 / 1984,
          },
        },
      },
    ]);
    const onSportChange = (title, areaSize = "full") => {
      showItems.value = false;
      const sport = sports.value.find((s) => s.title === title);
      if (!sport) return;
      currentSport.value.title = sport.title;
      currentSport.value.areas = sport.areas;
      currentSport.value.areaImage =
        currentSport.value.areas[areaSize]?.image || sport.areas.full.image;
      currentAreaSize.value = areaSize;

      // Set widthRel and heightRel based on selected area size
      if (sport.areas && sport.areas[areaSize]) {
        currentSport.value.widthRel = sport.areas[areaSize].widthRel;
        currentSport.value.heightRel = sport.areas[areaSize].heightRel;
      } else {
        currentSport.value.widthRel = sport.widthRel;
        currentSport.value.heightRel = sport.heightRel;
      }

      nextTick(() => {
        showItems.value = true;
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

    const showHeatmap = ref(true);
    const viewHeatmap = () => {
      showHeatmap.value = !showHeatmap.value;
      showMovement.value = false;
    };

    const showMovement = ref(false);
    const viewMovement = () => {
      showMovement.value = !showMovement.value;
      showHeatmap.value = false;
    };

    const showPlayerId = ref(false);
    const viewPlayerId = () => {
      showPlayerId.value = !showPlayerId.value;
    };

    const positionDataTopView = ref({});
    const metaDataTopView = ref({});

    function transformBBoxToPositionDataTopView(
      calibrationAssetId,
      bytetrackPluginId,
      updatedBboxes = null
    ) {
      calibrationAssetStore.loadCalibrationAsset(calibrationAssetId);

      if (updatedBboxes !== null) {
        bboxesStore.bboxDataActive = updatedBboxes;
        bboxesStore.bboxDataLoaded = true;
      } else {
        bboxesStore.loadBboxData(bytetrackPluginId);
      }

      if (bboxesStore.bboxDataActive && bboxesStore.bboxDataActive.length > 0) {
        // const _parsedData = JSON.parse(bboxesStore.bboxDataActive);

        const _bboxDataInterpolated = JSON.parse(bboxesStore.bboxDataActive);

        // const _bboxDataInterpolated = bboxesStore.interpolateBboxData(
        //   _parsedData,
        //   playerStore.videoFPS,
        //   30
        // );
        bboxesStore.bboxDataInterpolated = _bboxDataInterpolated;

        if (calibrationAssetStore.calibrationMatrix) {
          for (const [time, boxes] of Object.entries(_bboxDataInterpolated)) {
            positionDataTopView.value[time] = boxes.map((b) => {
              const { x, y } = calibrationAssetStore.applyHomography(
                calibrationAssetStore.calibrationMatrix,
                { x: b[3], y: b[4] }
              );
              b[3] = x;
              b[4] = y;
              return b;
            });
          }
        }
      }
    }

    const currentTime = ref(0);
    const currentTimeOffset = ref(0);
    const currentFrameKey = computed(() => {
      const time = playerStore.isSynced ? playerStore.currentTime : currentTime.value;

      return Object.keys(positionDataTopView.value)
        .map(Number)
        .sort((a, b) => a - b)
        .reduce(
          (prev, key) => (key <= Number(time) + Number(currentTimeOffset.value) ? key : prev),
          Object.keys(positionDataTopView.value)[0]
        );
    });

    return {
      topViewSize,
      setTopViewSize,
      currentSport,
      sports,
      onSportChange,
      currentAreaSize,
      showItems,
      showSpaceControl,
      viewSpaceControl,
      showEffectivePlayingSpace,
      viewEffectivePlayingSpace,
      showHeatmap,
      viewHeatmap,
      showMovement,
      viewMovement,
      positionDataTopView,
      metaDataTopView,
      transformBBoxToPositionDataTopView,
      showPlayerId,
      viewPlayerId,
      currentTime,
      currentFrameKey,
      currentTimeOffset,
    };
  },
  {
    persist: {
      pick: ["currentSport", "positionDataTopView"],
      storage: sessionStorage,
    },
  }
);
