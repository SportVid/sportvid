import { ref, computed } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";

export const useUserStore = defineStore(
  "user",
  () => {
    const loggedIn = ref(false);
    const userId = ref(null);
    const username = ref(null);
    const dateJoined = ref(null);
    const email = ref(null);
    const isLoading = ref(false);
    const role = ref(null);
    const usedStorageSize = ref(null);
    const maxStorageSize = ref(null);
    const remainingStorageSize = computed(() => {
      if (usedStorageSize.value === null || maxStorageSize.value === null) return null;
      return Math.max(0, maxStorageSize.value - usedStorageSize.value);
    });
    const maxVideoSize = ref(null);
    const maxFileSize = ref(null);
    const csrfToken = ref(null);

    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === name + "=") {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }
    async function getCSRFToken() {
      if (isLoading.value) return;

      isLoading.value = true;

      try {
        await axios.get(`${config.API_LOCATION}/user/csrf`, {
          withCredentials: true,
        });
        const token = getCookie("csrftoken");
        if (csrfToken.value !== token) {
          csrfToken.value = token;
        }
      } catch (error) {
        console.error("Error fetching CSRF token:", error);
      } finally {
        isLoading.value = false;
      }
    }

    async function getUserData() {
      if (isLoading.value) return;

      isLoading.value = true;

      try {
        const res = await axios.post(`${config.API_LOCATION}/user/get`);
        if (res.data.status === "ok") {
          userId.value = res.data.data.id || null;
          username.value = res.data.data.username || null;
          email.value = res.data.data.email || null;
          role.value = res.data.data.role || null;
          usedStorageSize.value = res.data.data.used_storage_size || 0;
          maxStorageSize.value = res.data.data.max_storage_size || 0;
          maxVideoSize.value = res.data.data.max_video_size || 0;
          maxFileSize.value = res.data.data.max_file_size || 0;
          dateJoined.value = res.data.data.date_joined || null;
          loggedIn.value = true;
        } else {
          userId.value = null;
          username.value = null;
          email.value = null;
          role.value = null;
          usedStorageSize.value = 0;
          maxStorageSize.value = 0;
          maxVideoSize.value = 0;
          maxFileSize.value = 0;
          dateJoined.value = null;
        }
      } catch (error) {
        console.error("Error fetching user data:", error);
      } finally {
        isLoading.value = false;
      }
    }

    async function login(params) {
      if (isLoading.value) return;

      isLoading.value = true;

      try {
        const res = await axios.post(`${config.API_LOCATION}/user/login`, { params });
        if (res.data.status === "ok") {
          userId.value = res.data.data.id || null;
          username.value = res.data.data.username || null;
          email.value = res.data.data.email || null;
          role.value = res.data.data.role || null;
          usedStorageSize.value = res.data.data.used_storage_size || 0;
          maxStorageSize.value = res.data.data.max_storage_size || 0;
          maxVideoSize.value = res.data.data.max_video_size || 0;
          maxFileSize.value = res.data.data.max_file_size || 0;
          dateJoined.value = res.data.data.date_joined || null;
          loggedIn.value = true;
          return res.data;
        }
        return res.data || { status: "error", message: "Invalid message." };
      } finally {
        isLoading.value = false;
      }
    }

    async function logout() {
      if (isLoading.value) return;

      isLoading.value = true;

      const params = { username: username.value };
      try {
        const res = await axios.post(`${config.API_LOCATION}/user/logout`, { params });
        if (res.data.status === "ok") {
          userId.value = null;
          username.value = null;
          email.value = null;
          role.value = null;
          usedStorageSize.value = 0;
          maxStorageSize.value = 0;
          maxVideoSize.value = 0;
          maxFileSize.value = 0;
          dateJoined.value = null;
          loggedIn.value = false;
          return true;
        }
      } finally {
        isLoading.value = false;
      }
    }

    async function register(params) {
      if (isLoading.value) return;

      isLoading.value = true;
      let res = null;

      try {
        res = await axios.post(`${config.API_LOCATION}/user/register`, { params });
        return res.data || { status: "error", message: "Invalid message." };
      } finally {
        isLoading.value = false;
        try {
          if (res && res.data && res.data.status === "ok") {
            await getUserData();
          }
        } catch (err) {
          console.error("Failed to fetch user data after registration:", err);
        }
      }
    }

    const accountDeleted = ref(false);

    async function updateUser(params) {
      if (isLoading.value) return;

      isLoading.value = true;

      try {
        const res = await axios.post(`${config.API_LOCATION}/user/update`, { params });
        if (res.data.status === "ok") {
          await getUserData();
        }
        return res.data || { status: "error", message: "Invalid message." };
      } finally {
        isLoading.value = false;
      }
    }

    async function deleteUser(params) {
      if (isLoading.value) return;

      isLoading.value = true;

      try {
        const res = await axios.post(`${config.API_LOCATION}/user/delete`, { params });
        if (res.data.status === "ok") {
          userId.value = null;
          username.value = null;
          email.value = null;
          role.value = null;
          usedStorageSize.value = 0;
          maxStorageSize.value = 0;
          maxVideoSize.value = 0;
          maxFileSize.value = 0;
          dateJoined.value = null;
          accountDeleted.value = true;
          loggedIn.value = false;
        }
        return res.data || { status: "error", message: "Invalid message." };
      } finally {
        isLoading.value = false;
      }
    }

    const showModalSettings = ref(false);
    function openSettings() {
      showModalSettings.value = true;
    }

    return {
      loggedIn,
      userId,
      username,
      dateJoined,
      email,
      role,
      isLoading,
      usedStorageSize,
      maxStorageSize,
      remainingStorageSize,
      maxVideoSize,
      maxFileSize,
      csrfToken,
      getCSRFToken,
      getUserData,
      login,
      logout,
      register,
      updateUser,
      deleteUser,
      showModalSettings,
      openSettings,
      accountDeleted,
    };
  },
  {
    persist: {
      pick: ["loggedIn"],
      storage: localStorage,
    },
  }
);
