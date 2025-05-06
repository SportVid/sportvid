import { defineStore } from "pinia";
import { nextTick, ref } from "vue";
import { useI18n } from "vue-i18n";

export const useTopViewStore = defineStore("top_view", () => {
  const { t } = useI18n();

  const showItems = ref(false);

  const topViewSize = ref({ width: 0, height: 0, top: 0, left: 0 });
  const setTopViewSize = (size) => {
    topViewSize.value = size;
  };

  const currentSport = ref({
    title: t("analysis_view.sports.soccer"),
    pitchImage: require("../assets/top-view/pitch_soccer.png"),
    widthRel: 2698 / 2910,
    heightRel: 1794 / 2010,
  });
  const sports = [
    {
      title: t("analysis_view.sports.soccer"),
      pitchImage: require("../assets/top-view/pitch_soccer.png"),
      widthRel: 2698 / 2910,
      heightRel: 1794 / 2010,
    },
    {
      title: t("analysis_view.sports.handball"),
      pitchImage: require("../assets/top-view/pitch_handball.png"),
      widthRel: 2428 / 2622,
      heightRel: 1216 / 1410,
    },
    {
      title: t("analysis_view.sports.basketball"),
      pitchImage: require("../assets/top-view/court_basketball.png"),
      widthRel: 2278 / 2460,
      heightRel: 1322 / 1504,
    },
    {
      title: t("analysis_view.sports.climbing"),
      pitchImage: require("../assets/top-view/area_climbing.png"),
      widthRel: 1492 / 2800,
      heightRel: 1866 / 1984,
    },
  ];
  const onSportChange = (title) => {
    showItems.value = false;
    const sport = sports.find((sport) => sport.title === title);
    currentSport.value.title = sport.title;
    currentSport.value.pitchImage = sport.pitchImage;
    currentSport.value.widthRel = sport.widthRel;
    currentSport.value.heightRel = sport.heightRel;
    nextTick(() => {
      showItems.value = true;
    });
  };

  return {
    topViewSize,
    setTopViewSize,
    currentSport,
    sports,
    onSportChange,
    showItems,
  };
});
