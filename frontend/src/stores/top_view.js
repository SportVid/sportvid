import { defineStore } from "pinia";
import { nextTick, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useBboxesStore } from "@/stores/bboxes";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

export const useTopViewStore = defineStore(
  "top_view",
  () => {
    const { t } = useI18n();

    const showItems = ref(false);

    const topViewSize = ref({ width: 0, height: 0, top: 0, left: 0 });
    const setTopViewSize = (size) => {
      topViewSize.value = size;
    };

    const currentSport = ref({
      title: t("sports.soccer"),
      pitchImage: require("../assets/top-view/pitch_soccer.png"),
      widthRel: 2698 / 2910,
      heightRel: 1794 / 2010,
    });
    const sports = ref([
      {
        title: t("sports.soccer"),
        pitchImage: require("../assets/top-view/pitch_soccer.png"),
        widthRel: 2698 / 2910,
        heightRel: 1794 / 2010,
      },
      {
        title: t("sports.handball"),
        pitchImage: require("../assets/top-view/pitch_handball.png"),
        widthRel: 2428 / 2622,
        heightRel: 1216 / 1410,
      },
      {
        title: t("sports.basketball"),
        pitchImage: require("../assets/top-view/court_basketball.png"),
        widthRel: 2278 / 2460,
        heightRel: 1322 / 1504,
      },
      {
        title: t("sports.climbing"),
        pitchImage: require("../assets/top-view/area_climbing.png"),
        widthRel: 1492 / 2800,
        heightRel: 1866 / 1984,
      },
    ]);
    const onSportChange = (title) => {
      showItems.value = false;
      const sport = sports.value.find((sport) => sport.title === title);
      currentSport.value.title = sport.title;
      currentSport.value.pitchImage = sport.pitchImage;
      currentSport.value.widthRel = sport.widthRel;
      currentSport.value.heightRel = sport.heightRel;
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

    const positionDataTopView = ref({});
    const metaDataTopView = ref({});

    const bboxesStore = useBboxesStore();
    const calibrationAssetStore = useCalibrationAssetStore();
    function transformBBoxToPositionDataTopView(calibrationAssetId, bytetrackPluginId) {
      calibrationAssetStore.loadCalibrationAsset(calibrationAssetId);
      bboxesStore.loadBboxData(bytetrackPluginId);

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

          // const _bboxDataTopView = ref({});
          // for (const [time, boxes] of Object.entries(_bboxDataInterpolated)) {
          //   _bboxDataTopView.value[time] = boxes.map((b) => {
          //     const { x, y } = calibrationAssetStore.applyHomography(
          //       calibrationAssetStore.calibrationMatrix,
          //       { x: b.top_x, y: b.top_y }
          //     );
          //     return { ...b, pos_x: x, pos_y: y };
          //   });
          // }
          // const times = Object.keys(_bboxDataTopView.value)
          //   .map(Number)
          //   .sort((a, b) => a - b);
          // if (times.length > 0) {
          //   const firstTimeKey = String(times[0]);
          //   const arr = _bboxDataTopView.value[firstTimeKey];
          //   if (Array.isArray(arr) && arr.length > 0) {
          //     arr[0] = { ...arr[0], team_id: "red" };
          //   }
          // }
          // positionDataTopView.value = _bboxDataTopView.value;
        }
      }
    }

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
    };
  }
  // {
  //   persist: {
  //     pick: ["positionDataTopView"],
  //     storage: sessionStorage,
  //   },
  // }
);
