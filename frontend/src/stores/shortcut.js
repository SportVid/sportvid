import { ref, computed } from 'vue';
import axios from '../plugins/axios';
import config from '../../app.config';
import { usePlayerStore } from '@/stores/player';
import * as Keyboard from "../plugins/keyboard.js";
import { defineStore } from 'pinia';

export const useShortcutStore = defineStore('shortcut', () => {
  const shortcuts = ref({});
  const shortcutList = ref([]);
  const shortcutByKeys = ref({});
  const isLoading = ref(false);

  const all = computed(() => {
    return shortcutList.value.map((id) => shortcuts.value[id]);
  });

  const get = (id) => {
    return shortcuts.value[id];
  };

  const getByKeys = (key) => {
    if (key in shortcutByKeys.value) {
      return shortcutByKeys.value[key].map((id) => shortcuts.value[id]);
    }
    return [];
  };

  const create = async ({ key, videoId = null }) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const params = {
      key: key,
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
      const res = await axios.post(`${config.API_LOCATION}/shortcut/create`, params);
      if (res.data.status === "ok") {
        const shortcut = res.data.entry;
        shortcuts.value[shortcut.id] = shortcut;
        shortcutList.value.push(shortcut.id);
        return res.data.entry.id;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const fetchForVideo = async ({ videoId = null }) => {
    if (isLoading.value) return;
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
      const res = await axios.get(`${config.API_LOCATION}/shortcut/list`, { params });
      if (res.data.status === "ok") {
        replaceAll(res.data.entries);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const clearStore = () => {
    shortcutByKeys.value = {};
    shortcuts.value = {};
    shortcutList.value = [];
  };

  const replaceAll = (newShortcuts) => {
    shortcuts.value = {};
    shortcutList.value = [];
    newShortcuts.forEach((e) => {
      shortcuts.value[e.id] = e;
      shortcutList.value.push(e.id);
    });
    updateKeyStore();
  };

  const updateKeyStore = () => {
    shortcutByKeys.value = {};
    all.value.forEach((e) => {
      const keys = Keyboard.generateKeysString(e.keys);
      if (!shortcutByKeys.value[keys]) {
        shortcutByKeys.value[keys] = [];
      }
      shortcutByKeys.value[keys].push(e.id);
    });
  };

  return {
    shortcuts,
    shortcutList,
    shortcutByKeys,
    isLoading,
    all,
    get,
    getByKeys,
    create,
    fetchForVideo,
    clearStore,
    replaceAll,
    updateKeyStore,
  };
});
