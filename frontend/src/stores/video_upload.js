import { ref } from 'vue';
import axios from '../plugins/axios';
import config from '../../app.config';
import { useVideoStore } from '@/stores/video';
import { useErrorStore } from '@/stores/error';
import { defineStore } from 'pinia';

export const useVideoUploadStore = defineStore('videoUpload', () => {
  const isUploading = ref(false);
  const progress = ref(0.0);

  const upload = async (params) => {
    const videoStore = useVideoStore();
    const formData = new FormData();
    formData.append("file", params.video.file);
    formData.append("title", params.video.title);
    formData.append("analyser", params.analyser);
    
    isUploading.value = true;

    try {
      const res = await axios.post(`${config.API_LOCATION}/video/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (event) => {
          const totalLength = event.lengthComputable
            ? event.total
            : event.target.getResponseHeader("content-length") ||
              event.target.getResponseHeader("x-decompressed-content-length");

          if (totalLength !== null) {
            const progressValue = Math.round((event.loaded * 100) / totalLength);
            progress.value = progressValue;
          }
        },
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
      isUploading.value = false;
      progress.value = 0;
    }
  };

  return {
    isUploading,
    progress,
    upload,
  };
});
