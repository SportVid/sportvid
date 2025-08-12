import { ref } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";

export const useTrackingDataStore = defineStore("trackingData", () => {
  const trackingDataList = ref([]);
  const trackingDataCurrent = ref(null);

  const isUploading = ref(false);
  const progress = ref(0);

  const uploadSuccess = ref(false);
  const renameSuccess = ref(false);
  const deleteSuccess = ref(false);

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

  const loadTrackingData = async (id) => {
    try {
      const res = await axios.get(`${config.API_LOCATION}/tracking_data/get`, {
        params: { id },
      });
      if (res.data.status === "ok") {
        trackingDataCurrent.value = res.data.entry;
      }
    } catch (error) {
      console.error("Failed to get tracking data:", error);
    }
  };

  const uploadTrackingData = async (file, title, format) => {
    if (!file || !title || !format) return;
    isUploading.value = true;
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title);
      formData.append("format", format);

      const res = await axios.post(`${config.API_LOCATION}/tracking_data/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (event) => {
          if (event.lengthComputable) {
            progress.value = Math.round((event.loaded * 100) / event.total);
          }
        },
      });

      if (res.data.status === "ok") {
        uploadSuccess.value = true;
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
        renameSuccess.value = true;
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
        deleteSuccess.value = true;
        await loadTrackingDataList();
      }
    } catch (error) {
      console.error("Failed to delete tracking data:", error);
    } finally {
    }
  };

  return {
    trackingDataList,
    trackingDataCurrent,
    uploadSuccess,
    renameSuccess,
    deleteSuccess,
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
