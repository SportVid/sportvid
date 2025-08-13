import { ref } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";

export const useTrackingDataStore = defineStore("trackingData", () => {
  const trackingDataList = ref([]);
  const trackingDataId = ref(null);
  const trackingDataCurrent = ref(null);

  const isUploading = ref(false);
  const progress = ref(0);

  const trackingDataUploadSuccess = ref(false);
  const trackingDataRenameSuccess = ref(false);
  const trackingDataDeleteSuccess = ref(false);

  const provider = [
    { name: "Kinexon", id: "kinexon" },
    { name: "DFL", id: "dfl" },
  ];

  const loadTrackingDataList = async () => {
    try {
      const res = await axios.get(`${config.API_LOCATION}/tracking_data/list`);
      if (res.data.status === "ok") {
        trackingDataList.value = res.data.entries;
      }
    } catch (error) {
      console.error("Failed to list tracking data:", error);
    }
  };

  const loadTrackingData = (id) => {
    const trackingData = trackingDataList.value.find((data) => data.id === id);
    if (trackingData) {
      trackingDataId.value = id;
      trackingDataCurrent.value = trackingData;
    }
  };

  const uploadTrackingData = async (params) => {
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
        trackingDataUploadSuccess.value = true;
        await loadTrackingDataList();
      }
    } catch (error) {
      console.error("Failed to upload tracking data:", error);
    } finally {
      isUploading.value = false;
      progress.value = 0;
    }
  };

  const renameTrackingData = async (id, newName) => {
    if (!id || !newName) return;
    try {
      const res = await axios.post(`${config.API_LOCATION}/tracking_data/rename`, {
        id,
        name: newName,
      });
      if (res.data.status === "ok") {
        trackingDataRenameSuccess.value = true;
        await loadTrackingDataList();
      }
    } catch (error) {
      console.error("Failed to rename tracking data:", error);
    } finally {
    }
  };

  const deleteTrackingData = async (id) => {
    if (!id) return;
    try {
      const res = await axios.post(`${config.API_LOCATION}/tracking_data/delete`, {
        id,
      });
      if (res.data.status === "ok") {
        trackingDataDeleteSuccess.value = true;
        await loadTrackingDataList();
      }
    } catch (error) {
      console.error("Failed to delete tracking data:", error);
    } finally {
    }
  };

  return {
    trackingDataList,
    trackingDataId,
    trackingDataCurrent,
    trackingDataUploadSuccess,
    trackingDataRenameSuccess,
    trackingDataDeleteSuccess,
    loadTrackingDataList,
    loadTrackingData,
    uploadTrackingData,
    renameTrackingData,
    deleteTrackingData,
    isUploading,
    progress,
    provider,
  };
});
