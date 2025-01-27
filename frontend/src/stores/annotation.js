import { ref, reactive, computed } from 'vue';
import axios from '../plugins/axios';
import config from '../../app.config';
import { defineStore } from 'pinia';
import { usePlayerStore } from "@/stores/player";
import { useAnnotationCategoryStore } from "@/stores/annotation_category";

export const useAnnotationStore = defineStore('annotation', () => {
  const annotations = reactive({});
  const isLoading = ref(false);

  const nonTranscripts = computed(() => {
    const annotationCategoryStore = useAnnotationCategoryStore();
    return Object.values(annotations).filter((a) => {
      const category = annotationCategoryStore.get(a.category_id);
      return !category || category.name !== "Transcript";
    });
  });

  const all = computed(() => Object.values(annotations));

  const getAnnotation = (id) => annotations[id];

  const create = async ({ name, color, categoryId, videoId = null }) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const params = {
      name,
      color,
      category_id: categoryId || undefined,
      video_id: videoId || usePlayerStore().videoId,
    };

    try {
      const res = await axios.post(`${config.API_LOCATION}/annotation/create`, params);
      if (res.data.status === "ok") {
        addToStore([res.data.entry]);
        return res.data.entry.id;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const change = async ({ annotationId, name, color, categoryId }) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const params = {
      annotation_id: annotationId,
      name,
      color,
      category_id: categoryId || undefined,
    };

    try {
      const res = await axios.post(`${config.API_LOCATION}/annotation/update`, params);
      if (res.data.status === "ok") {
        updateInStore([{ id: annotationId, name, color, category_id: categoryId }]);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const fetchForVideo = async ({ videoId = null }) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const params = {
      video_id: videoId || usePlayerStore().videoId,
    };

    try {
      const res = await axios.get(`${config.API_LOCATION}/annotation/list`, { params });
      if (res.data.status === "ok") {
        updateStore(res.data.entries);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const clearStore = () => {
    Object.keys(annotations).forEach((key) => {
      delete annotations[key];
    });
  };

  const updateInStore = (newAnnotations) => {
    newAnnotations.forEach((e) => {
      annotations[e.id] = e;
    });
  };

  const addToStore = (newAnnotations) => {
    newAnnotations.forEach((e) => {
      annotations[e.id] = e;
    });
  };

  const updateStore = (newAnnotations) => {
    newAnnotations.forEach((e) => {
      if (!(e.id in annotations)) {
        annotations[e.id] = e;
      }
    });
  };

  return {
    annotations,
    isLoading,
    nonTranscripts,
    all,
    getAnnotation,
    create,
    change,
    fetchForVideo,
    clearStore,
    updateInStore,
    addToStore,
    updateStore,
  };
});
