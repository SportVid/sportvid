import { computed } from 'vue';
import { defineStore } from 'pinia';
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export const useBBoxesStore = defineStore("bboxes", () => {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();

  const bboxData = computed(() => {
    let _bboxData = pluginRunStore
      .forVideo(playerStore.videoId)
      .filter((e) => e.type == "bytetrack" && e.status == "DONE")
      .slice(-1)
      .map((e) => {
        e.results = pluginRunResultStore.forPluginRun(e.id);
        return e;
      });
      console.debug("bboxData: ", JSON.stringify(_bboxData));
      return _bboxData;
  });

  return {
    bboxData,
  };
});
