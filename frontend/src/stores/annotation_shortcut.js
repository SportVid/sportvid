import axios from '../plugins/axios';
import config from '../../app.config';
import { defineStore } from 'pinia';
import { usePlayerStore } from '@/stores/player';
import { useShortcutStore } from '@/stores/shortcut';
import { ref, reactive, computed } from 'vue';

export const useAnnotationShortcutStore = defineStore('annotationShortcut', () => {
  const annotationShortcuts = reactive({});
  const annotationShortcutList = ref([]);
  const annotationShortcutByKeys = reactive({});
  const isLoading = ref(false);

  const all = computed(() => {
    return annotationShortcutList.value.map(
      (id) => annotationShortcuts[id]
    );
  });

  const get = computed(() => (id) => annotationShortcuts[id]);

  const forShortcut = computed(() => (shortcutId) => {
    const annotationShortcutsList = annotationShortcutList.value
      .map((id) => annotationShortcuts[id])
      .filter((e) => e.shortcut_id === shortcutId);

    if (annotationShortcutsList.length > 0) {
      return annotationShortcutsList[0];
    }
    return null;
  });

  const update = async ({ annotationShortcutsData, videoId = null }) => {
    if (isLoading.value) {
      return;
    }
    isLoading.value = true;

    const params = {
      annotation_shortcuts: annotationShortcutsData,
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
      const res = await axios.post(`${config.API_LOCATION}/annotation/shortcut/update`, params);
      if (res.data.status === 'ok') {
        replaceAll(res.data.annotation_shortcuts);

        const shortcutStore = useShortcutStore();
        shortcutStore.replaceAll(res.data.shortcuts);
      }
    } catch (error) {
      console.error('Error updating annotation shortcuts:', error);
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
      const res = await axios.get(`${config.API_LOCATION}/annotation/shortcut/list`, {
        params,
      });
      if (res.data.status === 'ok') {
        replaceAll(res.data.entries);
      }
    } catch (error) {
      console.error('Error fetching annotation shortcuts:', error);
    } finally {
      isLoading.value = false;
    }
  };

  const clearStore = () => {
    annotationShortcutByKeys.value = {};
    annotationShortcuts.value = {};
    annotationShortcutList.value = [];
  };

  const replaceAll = (annotationShortcutsData) => {
    annotationShortcuts.value = {};
    annotationShortcutList.value = [];
    annotationShortcutsData.forEach((e) => {
      annotationShortcuts.value[e.id] = e;
      annotationShortcutList.value.push(e.id);
    });
  };

  return {
    annotationShortcuts,
    annotationShortcutList,
    annotationShortcutByKeys,
    isLoading,
    all,
    get,
    forShortcut,
    update,
    fetchForVideo,
    clearStore,
    replaceAll,
  };
});
