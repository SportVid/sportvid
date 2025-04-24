<template>
  <v-app>
    <v-app-bar>
      <template #prepend>
        <img :title="appName" src="./assets/logo_tib_dshs.png" height="50" class="ml-1 mr-2" />
        <v-app-bar-title class="text-h5 text-primary">
          {{ $t("app_bar.plattform_name") }}
        </v-app-bar-title>
      </template>

      <template #append>
        <v-btn v-if="analysisView" to="/">
          <v-icon color="primary">mdi-movie</v-icon>
          {{ $t("app_bar.video_view") }}
        </v-btn>
        <ModalPluginButton v-if="analysisView" />
        <ModalHistoryButton v-if="analysisView" />
        <ModalShortcutButton v-if="analysisView" />
        <ModalExportButton v-if="analysisView" />
        <v-divider vertical inset class="mx-2" />
        <UserMenu />
      </template>
    </v-app-bar>
    <router-view />
    <ModalError />
  </v-app>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import ModalPluginButton from "@/components/ModalPluginButton.vue";
import ModalHistoryButton from "./components/ModalHistoryButton.vue";
import ModalShortcutButton from "@/components/ModalShortcutButton.vue";
import ModalExportButton from "@/components/ModalExportButton.vue";
import UserMenu from "@/components/UserMenu.vue";
import ModalError from "./components/ModalError.vue";

const route = useRoute();

const appName = process.env.VUE_APP_NAME;

const analysisView = computed(() => route.name === "AnalysisView");
</script>
