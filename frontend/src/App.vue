<template>
  <v-app id="sportVid">
    <v-app-bar>
      <img :title="appName" src="./assets/logo_tib_dshs.png" height="50" class="ml-4" />
      <v-toolbar-title class="pr-12">{{ $t("app_bar.plattform_name") }}</v-toolbar-title>

      <v-btn v-if="analysisView" to="/">
        <v-icon color="primary">mdi-movie</v-icon>
        {{ $t("app_bar.video_view") }}
      </v-btn>
      <PluginMenu v-if="analysisView" />
      <HistoryMenu v-if="analysisView" />
      <ShortcutMenu v-if="analysisView" />
      <ExportMenu v-if="analysisView" />
      <v-divider vertical inset class="mx-2" />
      <UserMenu />
    </v-app-bar>
    <router-view />
    <ModalError />
  </v-app>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import PluginMenu from "@/components/PluginMenu.vue";
import HistoryMenu from "./components/HistoryMenu.vue";
import ShortcutMenu from "@/components/ShortcutMenu.vue";
import ExportMenu from "@/components/ExportMenu.vue";
import UserMenu from "@/components/UserMenu.vue";
import ModalError from "./components/ModalError.vue";

const route = useRoute();

const appName = process.env.VUE_APP_NAME;

const analysisView = computed(() => route.name === "AnalysisView");
</script>
