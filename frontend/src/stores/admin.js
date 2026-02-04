import { ref } from "vue";
import { defineStore } from "pinia";
import axios from "../plugins/axios";
import config from "../../app.config";

export const useAdminStore = defineStore("admin", () => {
  const users = ref([]);
  const isLoading = ref(false);
  const error = ref(null);

  async function fetchUsers() {
    if (isLoading.value) return;

    isLoading.value = true;
    error.value = null;

    try {
      const res = await axios.get(`${config.API_LOCATION}/user/admin/user/list`, {
        withCredentials: true,
      });

      if (res.data.status === "ok") {
        users.value = res.data.data;
      } else {
        error.value = res.data.error || "Unknown error";
      }
    } catch (err) {
      console.error("Failed to fetch users:", err);
      error.value = "network_error";
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
        users.value = users.value.filter((u) => u.id !== params.id);
      }
      return res.data;
    } finally {
      isLoading.value = false;
    }
  }

  async function updateUser(params) {
    if (isLoading.value) return;
    isLoading.value = true;

    try {
      const res = await axios.post(`${config.API_LOCATION}/user/update`, { params });
      if (res.data.status === "ok") {
        const idx = users.value.findIndex((u) => u.id === params.id);
        if (idx !== -1) users.value[idx] = res.data.data;
      }
      return res.data;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    users,
    isLoading,
    error,
    fetchUsers,
    deleteUser,
    updateUser,
  };
});
