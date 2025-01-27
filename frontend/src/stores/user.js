import { ref } from "vue";
import { defineStore } from 'pinia';
import axios from '../plugins/axios';
import config from '../../app.config';

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export const useUserStore = defineStore('user', () => {
  const loggedIn = ref(false);
  const username = ref(null);
  const date = ref(null);
  const email = ref(null);
  const isLoading = ref(false);
  const allowance = ref(null);
  const maxVideoSize = ref(null);
  const csrfToken = ref(null);

  async function getCSRFToken() {
    if (isLoading.value) return;

    isLoading.value = true;

    try {
      await axios.get(`${config.API_LOCATION}/user/csrf`, {
        withCredentials: true,
      });
      const token = getCookie('csrftoken');
      if (csrfToken.value !== token) {
        csrfToken.value = token;
      }
    } catch (error) {
      console.error('Error fetching CSRF token:', error);
    } finally {
      isLoading.value = false;
    }
  }

  async function getUserData() {
    if (isLoading.value) return;

    isLoading.value = true;

    try {
      const res = await axios.post(`${config.API_LOCATION}/user/get`);
      if (res.data.status === 'ok') {
        username.value = res.data.data.username || null;
        email.value = res.data.data.email || null;
        date.value = res.data.data.date || null;
        allowance.value = res.data.data.allowance || 0;
        maxVideoSize.value = res.data.data.max_video_size || 0;
        loggedIn.value = true;
      } else {
        username.value = null;
        email.value = null;
        loggedIn.value = false;
        allowance.value = 0;
        maxVideoSize.value = 0;
      }
    } catch (error) {
      console.error('Error fetching user data:', error);
    } finally {
      isLoading.value = false;
    }
  }

  async function login(params) {
    if (isLoading.value) return;

    isLoading.value = true;

    try {
      const res = await axios.post(`${config.API_LOCATION}/user/login`, { params });
      if (res.data.status === 'ok') {
        username.value = res.data.data.username || null;
        email.value = res.data.data.email || null;
        date.value = res.data.data.date || null;
        allowance.value = res.data.data.allowance || 0;
        maxVideoSize.value = res.data.data.max_video_size || 0;
        loggedIn.value = true;
        return res.data;
      }
      return res.data || { status: 'error', message: 'Invalid message.' };
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
      if (res.data.status === 'ok') {
        username.value = null;
        email.value = null;
        date.value = null;
        allowance.value = 0;
        maxVideoSize.value = 0;
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

    try {
      const res = await axios.post(`${config.API_LOCATION}/user/register`, { params });
      if (res.data.status === 'ok') {
        await getUserData();
      }
      return res.data || { status: 'error', message: 'Invalid message.' };
    } finally {
      isLoading.value = false;
    }
  }

  return {
    loggedIn,
    username,
    date,
    email,
    isLoading,
    allowance,
    maxVideoSize,
    csrfToken,
    getCSRFToken,
    getUserData,
    login,
    logout,
    register,
  };
});
