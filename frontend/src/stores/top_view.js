import { defineStore } from "pinia";
import { ref } from "vue";

export const useTopViewStore = defineStore("top_view", () => {
  const topViewSize = ref({ width: 0, height: 0, top: 0, left: 0 });

  const setTopViewSize = (size) => {
    topViewSize.value = size;
  };

  const currentSport = ref({
    title: "Soccer",
    pitchImage: require("../assets/pitch_soccer.png"),
    widthRel: 2698 / 2910,
    heightRel: 1794 / 2010,
  });

  const sports = [
    {
      title: "Soccer",
      pitchImage: require("../assets/pitch_soccer.png"),
      widthRel: 2698 / 2910,
      heightRel: 1794 / 2010,
    },
    {
      title: "Handball",
      pitchImage: require("../assets/pitch_handball.png"),
      widthRel: 2428 / 2622,
      heightRel: 1216 / 1410,
    },
    {
      title: "Basketball",
      pitchImage: require("../assets/court_basketball.png"),
      widthRel: 2278 / 2460,
      heightRel: 1322 / 1504,
    },
    {
      title: "Climbing",
      pitchImage: require("../assets/area_climbing.png"),
      widthRel: 1492 / 2800,
      heightRel: 1866 / 1984,
    },
  ];

  const onSportChange = (title) => {
    const sport = sports.find((sport) => sport.title === title);
    currentSport.value.title = sport.title;
    currentSport.value.pitchImage = sport.pitchImage;
    currentSport.value.widthRel = sport.widthRel;
    currentSport.value.heightRel = sport.heightRel;
  };

  return {
    topViewSize,
    setTopViewSize,
    currentSport,
    sports,
    onSportChange,
  };
});
