import { ref } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";

export const usePositionDataStore = defineStore("position_data", () => {
  const positionDataList = ref([]);
  const positionDataId = ref(null);
  const positionDataCurrent = ref(null);

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
    const positionData = positionDataList.value.find((data) => data.id === id);
    if (positionData) {
      positionDataId.value = id;
      positionDataCurrent.value = positionData;
    }
  };

  const uploadPositionData = async (params) => {
    if (!params) return;
    isUploading.value = true;
    try {
      const formData = new FormData();
      formData.append("file", params.file);
      formData.append("title", params.title);
      formData.append("format", params.format);

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
    positionDataCurrent,
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
