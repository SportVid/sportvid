import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { usePositionDataStore } from "@/stores/position_data";

export const useFileStore = defineStore("file", () => {
  const positionDataStore = usePositionDataStore();

  const files = ref({});
  const fileList = ref([]);
  const all = computed(() => positionDataStore.positionDataList.map((id) => files.value[id]));

  return {
    files,
    fileList,
    all,
  };
});
