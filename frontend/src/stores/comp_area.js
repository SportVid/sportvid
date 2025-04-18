import { defineStore } from "pinia";
import { ref } from "vue";

export const useCompAreaStore = defineStore("comp_area", () => {
  const compAreaSize = ref({ width: 0, height: 0, top: 0, left: 0 });

  const setCompAreaSize = (size) => {
    compAreaSize.value = size;
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

  const onSportChange = (idx) => {
    currentSport.value = sports[idx];
  };

  return {
    compAreaSize,
    setCompAreaSize,
    currentSport,
    sports,
    onSportChange,
  };
});
