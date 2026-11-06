import axios from "../plugins/axios";
import config from "../../app.config";
import { useVideoStore } from "@/stores/video";
import { useErrorStore } from "@/stores/error";
import { defineStore } from "pinia";
import { useUploadTracker } from "@/composables/useUploadTracker";

export const useVideoUploadStore = defineStore("videoUpload", () => {
  const { isUploading, progress, etaSeconds: uploadEtaSeconds, start, finish, onUploadProgress } =
    useUploadTracker();

  const upload = async (params) => {
    const videoStore = useVideoStore();
    const formData = new FormData();
    formData.append("file", params.video.file);
    formData.append("title", params.video.title);
    formData.append("analyser", params.analyser);
    formData.append("fieldLength", params.video.fieldLength);
    formData.append("fieldWidth", params.video.fieldWidth);
    formData.append("division", params.video.division);
    formData.append("currentPosition", params.video.currentPosition);
    formData.append("totalNumberofTeams", params.video.totalNumberofTeams);
    formData.append("ageGroup", params.video.ageGroup);
    formData.append("sport", params.video.sport);

    start();

    try {
      const res = await axios.post(`${config.API_LOCATION}/video/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress,
      });

      if (res.data.status === "ok") {
        res.data.entries.forEach((entry) => {
          videoStore.addToStore(entry);
        });
      }
    } catch (error) {
      const errorStore = useErrorStore();
      if (error.response.data) {
        if (error.response.data.hasOwnProperty("type")) {
          errorStore.setError("video_upload", error.response.data.type);
        }
      } else {
        errorStore.setError("video_upload", "unknown");
      }
    } finally {
      finish();
    }
  };

  return {
    isUploading,
    progress,
    uploadEtaSeconds,
    upload,
  };
});
