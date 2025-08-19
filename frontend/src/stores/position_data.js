import { ref } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export const usePositionDataStore = defineStore("position_data", () => {
  const playerStore = usePlayerStore();
  const pluginRunStore = usePluginRunStore();
  const pluginRunResultStore = usePluginRunResultStore();

  const positionDataList = ref([]);
  const positionDataId = ref(null);
  const positionDataActive = ref(null);

  const isUploading = ref(false);
  const progress = ref(0);

  const positionDataUploadSuccess = ref(false);
  const positionDataRenameSuccess = ref(false);
  const positionDataDeleteSuccess = ref(false);

  const provider = [
    { name: "Kinexon", id: "kinexon" },
    { name: "DFL", id: "dfl" },
  ];

  const loadPositionDataList = async () => {
    try {
      const res = await axios.get(`${config.API_LOCATION}/tracking_data/list`);
      if (res.data.status === "ok") {
        positionDataList.value = res.data.entries;
      }
    } catch (error) {
      console.error("Failed to list tracking data:", error);
    }
  };

  const loadPositionData = (id) => {
    const selectedPositionData = positionDataList.value.find((data) => data.id === id);
    if (selectedPositionData) {
      positionDataId.value = id;

      positionDataActive.value = pluginRunStore
        .forVideo(playerStore.videoId)
        .filter(
          (e) => e.type === "posdata_convert" && e.status === "DONE" && e.tracking_data_id === id
        )
        .map((e) => {
          e.results = pluginRunResultStore.forPluginRun(e.id);
          return e;
        });

      console.log("PosData", positionDataId.value, positionDataActive.value);
    }
  };

  const uploadPositionData = async (params) => {
    if (!params) return;
    isUploading.value = true;
    try {
      const formData = new FormData();
      formData.append("video_id", playerStore.videoId);
      formData.append("title", params.title);
      formData.append("format", params.format);
      formData.append("file", params.file);
      formData.append("meta_data", params.meta_data);
      formData.append("delimiter", params.delimiter);
      formData.append("fps", params.fps);

      const res = await axios.post(`${config.API_LOCATION}/tracking_data/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (event) => {
          if (event.lengthComputable) {
            progress.value = Math.round((event.loaded * 100) / event.total);
          }
        },
      });

      if (res.data.status === "ok") {
        positionDataUploadSuccess.value = true;
        await loadPositionDataList();
      }
    } catch (error) {
      console.error("Failed to upload position data:", error);
    } finally {
      isUploading.value = false;
      progress.value = 0;
    }
  };

  const renamePositionData = async (id, newName) => {
    if (!id || !newName) return;
    try {
      const res = await axios.post(`${config.API_LOCATION}/tracking_data/rename`, {
        id,
        name: newName,
      });
      if (res.data.status === "ok") {
        positionDataRenameSuccess.value = true;
        await loadPositionDataList();
      }
    } catch (error) {
      console.error("Failed to rename position data:", error);
    } finally {
    }
  };

  const deletePositionData = async (id) => {
    if (!id) return;
    try {
      const res = await axios.post(`${config.API_LOCATION}/tracking_data/delete`, {
        id,
      });
      if (res.data.status === "ok") {
        positionDataDeleteSuccess.value = true;
        await loadPositionDataList();
      }
    } catch (error) {
      console.error("Failed to delete position data:", error);
    } finally {
    }
  };

  return {
    positionDataList,
    positionDataId,
    positionDataActive,
    positionDataUploadSuccess,
    positionDataRenameSuccess,
    positionDataDeleteSuccess,
    loadPositionDataList,
    loadPositionData,
    uploadPositionData,
    renamePositionData,
    deletePositionData,
    isUploading,
    progress,
    provider,
  };
});
