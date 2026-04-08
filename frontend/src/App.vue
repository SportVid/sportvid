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
import AppBar from "@/components/app/app-bar/AppBar.vue";
import ModalError from "@/components/app/ModalError.vue";
import AppFooter from "./components/app/AppFooter.vue";

const theme = useTheme();
const themeStore = useThemeStore();
const videoStore = useVideoStore();
const userStore = useUserStore();

theme.global.name.value = themeStore.isDark ? "dark" : "light";

watch(
  () => themeStore.isDark,
  (isDark) => {
    theme.global.name.value = isDark ? "dark" : "light";
  }
);

onMounted(() => {
  if (userStore.loggedIn) {
    videoStore.fetchAll();
  }
});

watch(
  () => userStore.loggedIn,
  (newValue, oldValue) => {
    if (!oldValue && newValue) {
      videoStore.fetchAll();
    }
  }
);
</script>
