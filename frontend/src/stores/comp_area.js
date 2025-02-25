import { defineStore } from "pinia";
import { ref } from "vue";

export const useCompAreaStore = defineStore("comp_area", () => {
    const compAreaSize = ref({ width: 0, height: 0, top: 0, left: 0 });

    const setCompAreaSize = (size) => {
      compAreaSize.value = size;
    };

    return {
      compAreaSize,
      setCompAreaSize,
    };
});