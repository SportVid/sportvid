<template>
  <v-app id="sportVid">
    <v-app-bar>
      <img :title="appName" src="./assets/logo_tib_dshs.png" height="50" class="ml-4" />
      <v-toolbar-title class="pr-12">{{ $t("app_bar.plattform_name") }}</v-toolbar-title>

      <v-btn v-if="analysisView" to="/">
        <v-icon color="primary">mdi-movie</v-icon>
        {{ $t("app_bar.video_view") }}
      </v-btn>
      <ModalPluginButton v-if="analysisView" />
      <ModalHistoryButton v-if="analysisView" />
      <ModalShortcutButton v-if="analysisView" />
      <ModalExportButton v-if="analysisView" />
      <v-divider vertical inset class="mx-2" />
      <ModalUserMenu />
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
import ModalUserMenu from "@/components/ModalUserMenu.vue";
import ModalError from "./components/ModalError.vue";

const route = useRoute();

const appName = process.env.VUE_APP_NAME;

const analysisView = computed(() => route.name === "AnalysisView");
</script>
