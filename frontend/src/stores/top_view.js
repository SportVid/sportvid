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

    const currentSport = ref({
      title: t("sports.soccer"),
      areaImage: require("../assets/top-view/pitch_soccer.png"),
      areaImages: {
        full: require("../assets/top-view/pitch_soccer.png"),
        half: require("../assets/top-view/pitch_soccer.png"),
        penToPen: require("../assets/top-view/pitch_soccer.png"),
        doublePen: require("../assets/top-view/pitch_soccer.png"),
      },
      templateCrops: {
        full: { x: [0, 1], y: [0, 1] },
        half: { x: [0, 0.5], y: [0, 1] },
        penToPen: { x: [0.16, 0.84], y: [0, 1] },
        doublePen: { x: [0, 0.32], y: [0.18, 0.82] },
      },
      widthRel: 2698 / 2910,
      heightRel: 1794 / 2010,
    });
    const sports = ref([
      {
        title: t("sports.soccer"),
        areaImage: require("../assets/top-view/pitch_soccer.png"),
        areaImages: {
          full: require("../assets/top-view/pitch_soccer.png"),
          half: require("../assets/top-view/pitch_soccer.png"),
          penToPen: require("../assets/top-view/pitch_soccer.png"),
          doublePen: require("../assets/top-view/pitch_soccer.png"),
        },
        templateCrops: {
          full: { x: [0, 1], y: [0, 1] },
          half: { x: [0, 0.5], y: [0, 1] },
          penToPen: { x: [0.16, 0.84], y: [0, 1] },
          doublePen: { x: [0, 0.32], y: [0.18, 0.82] },
        },
        widthRel: 2698 / 2910,
        heightRel: 1794 / 2010,
      },
      {
        title: t("sports.handball"),
        areaImages: {
          full: require("../assets/top-view/pitch_handball.png"),
          half: require("../assets/top-view/pitch_handball.png"),
        },
        templateCrops: {
          full: { x: [0, 1], y: [0, 1] },
          half: { x: [0, 0.5], y: [0, 1] },
        },
        widthRel: 2428 / 2622,
        heightRel: 1216 / 1410,
      },
      {
        title: t("sports.basketball"),
        areaImages: {
          full: require("../assets/top-view/court_basketball.png"),
          half: require("../assets/top-view/court_basketball.png"),
        },
        templateCrops: {
          full: { x: [0, 1], y: [0, 1] },
          half: { x: [0, 0.5], y: [0, 1] },
        },
        widthRel: 2278 / 2460,
        heightRel: 1322 / 1504,
      },
      {
        title: t("sports.climbing"),
        areaImages: { full: require("../assets/top-view/area_climbing.png") },
        templateCrops: {
          full: { x: [0, 1], y: [0, 1] },
        },
        widthRel: 1492 / 2800,
        heightRel: 1866 / 1984,
      },
    ]);
    const onSportChange = (title, areaSize = null) => {
      showItems.value = false;
      const sport = sports.value.find((s) => s.title === title);
      if (!sport) return;
      currentSport.value.title = sport.title;
      currentSport.value.widthRel = sport.widthRel;
      currentSport.value.heightRel = sport.heightRel;

      currentSport.value.areaImages = sport.areaImages || { full: sport.areaImages?.full };
      const tpl = areaSize && currentSport.value.areaImages[areaSize] ? areaSize : "full";
      currentSport.value.template = tpl;
      currentSport.value.areaImage =
        currentSport.value.areaImages[tpl] || Object.values(currentSport.value.areaImages)[0];

      currentSport.value.fieldLength = null;
      currentSport.value.fieldWidth = null;
      nextTick(() => {
        showItems.value = true;
      });
    };

    const setTemplateSelection = (template, fieldLength = null, fieldWidth = null) => {
      currentSport.value.template = template || "full";
      currentSport.value.fieldLength = fieldLength;
      currentSport.value.fieldWidth = fieldWidth;

      // compute approximate widthRel/heightRel adjustments if user provided sizes
      if (fieldWidth && fieldLength) {
        // store ratio of length/width as proxy to adjust display aspect
        currentSport.value.widthRel = fieldWidth / Math.max(fieldWidth, fieldLength);
        currentSport.value.heightRel = fieldLength / Math.max(fieldWidth, fieldLength);
      }
      // set the selected area image when template changes (if available)
      if (currentSport.value.areaImages && currentSport.value.areaImages[template]) {
        currentSport.value.areaImage = currentSport.value.areaImages[template];
      }
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
      setTemplateSelection,
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
