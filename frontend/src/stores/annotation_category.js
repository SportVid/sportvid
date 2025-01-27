import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from '../plugins/axios';
import config from '../../app.config';
import { usePlayerStore } from "@/stores/player";

export const useAnnotationCategoryStore = defineStore('annotationCategory', () => {
  const annotationCategories = ref({});
  const isLoading = ref(false);

  const all = computed(() => {
    return Object.values(annotationCategories.value);
  });

  const get = (id) => {
    return annotationCategories.value[id];
  };

  const create = async ({ name, color, videoId = null }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    const params = {
      name,
      color,
    };
    if (videoId) {
      params.video_id = videoId;
    } else {
      const playerStore = usePlayerStore();
      const videoId = playerStore.videoId;
      if (videoId) {
        params.video_id = videoId;
      }
    }

    try {
      const res = await axios.post(`${config.API_LOCATION}/annotation/category/create`, params);
      if (res.data.status === 'ok') {
        addToStore([res.data.entry]);
        return res.data.entry.id;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const fetchForVideo = async ({ videoId = null }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    let params = {};

    if (videoId) {
      params.video_id = videoId;
    } else {
      const playerStore = usePlayerStore();
      const videoId = playerStore.videoId;
      if (videoId) {
        params.video_id = videoId;
      }
    }

    try {
      const res = await axios.get(`${config.API_LOCATION}/annotation/category/list`, { params });
      if (res.data.status === 'ok') {
        updateStore(res.data.entries);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const clearStore = () => {
    Object.keys(annotationCategories.value).forEach((key) => {
      delete annotationCategories.value[key];
    });
  };

  const addToStore = (categories) => {
    categories.forEach((e) => {
      annotationCategories.value[e.id] = e;
    });
  };

  const updateStore = (categories) => {
    categories.forEach((e) => {
      if (!(e.id in annotationCategories.value)) {
        annotationCategories.value[e.id] = e;
      }
    });
  };

  return {
    annotationCategories,
    isLoading,
    all,
    get,
    create,
    fetchForVideo,
    clearStore,
    addToStore,
    updateStore,
  };
});
