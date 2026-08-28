<template>
  <v-app>
    <AppBar />
    <router-view />
    <ModalError />
    <AppFooter />
  </v-app>
</template>

<script setup>
import { watch, onMounted } from "vue";
import { useTheme } from "vuetify";
import { useThemeStore } from "@/stores/theme";
import { useVideoStore } from "@/stores/video";
import { useUserStore } from "@/stores/user";
import { useEventStreamStore } from "@/stores/event_stream";
import AppBar from "@/components/app/app-bar/AppBar.vue";
import ModalError from "@/components/app/ModalError.vue";
import AppFooter from "./components/app/AppFooter.vue";

const theme = useTheme();
const themeStore = useThemeStore();
const videoStore = useVideoStore();
const userStore = useUserStore();
const eventStreamStore = useEventStreamStore();

const updateFavicon = (isDark) => {
  const link = document.querySelector("link[rel='icon']");
  if (link) link.href = isDark ? "/favicon_dshs_marburg_dark.png" : "/favicon_dshs_marburg_light.png";
};

theme.change(themeStore.isDark ? "dark" : "light");
updateFavicon(themeStore.isDark);

watch(
  () => themeStore.isDark,
  (isDark) => {
    theme.change(isDark ? "dark" : "light");
    updateFavicon(isDark);
  }
);

onMounted(() => {
  if (userStore.loggedIn) {
    videoStore.fetchAll();
    // One connection for the whole app: plugin run and video state changes are pushed
    // in instead of being polled for by the individual views.
    eventStreamStore.connect();
  }
});

watch(
  () => userStore.loggedIn,
  (newValue, oldValue) => {
    if (!oldValue && newValue) {
      videoStore.fetchAll();
      eventStreamStore.connect();
    } else if (oldValue && !newValue) {
      eventStreamStore.disconnect();
    }
  }
);
</script>
