<template>
  <v-app-bar>
    <template #prepend>
      <img src="@/assets/logo_tib_dshs.png" height="50" class="ml-1 mr-2" />
      <v-app-bar-title class="text-h5 text-primary">
        {{ $t("plattform.title") }}
      </v-app-bar-title>
    </template>

    <template #append>
      <v-btn v-if="(termsOfUseView || guidelinesView) && !loggedIn" to="/">
        <app-bar-icon>mdi-home</app-bar-icon>
        <span class="text-primary">
          {{ $t("app_bar.home") }}
        </span>
      </v-btn>

      <v-btn v-if="!videoView && loggedIn" to="/">
        <app-bar-icon>mdi-movie</app-bar-icon>
        <span class="text-primary">{{ $t("app_bar.video_view") }}</span>
      </v-btn>

      <div v-if="analysisView" class="d-flex align-center" data-tour="analysis-appbar-actions">
        <v-btn @click="showModalPlugin = true" data-tour="modal-plugin-open">
          <app-bar-icon>mdi-plus</app-bar-icon>
          <span class="text-primary">{{ $t("app_bar.plugin_menu") }}</span>
        </v-btn>

        <v-btn @click="showModalHistory = true" data-tour="modal-history-open">
          <app-bar-icon>mdi-history</app-bar-icon>
          <v-badge
            v-if="numRunningPlugins > 0"
            color="accent"
            :content="numRunningPlugins"
            floating
          >
            <span class="text-primary">{{ $t("app_bar.history_menu") }}</span>
          </v-badge>
          <span v-else>
            <span class="text-primary">{{ $t("app_bar.history_menu") }}</span>
          </span>
        </v-btn>

        <v-btn @click="showModalShortcut = true">
          <app-bar-icon>mdi-label-multiple-outline</app-bar-icon>
          <span class="text-primary">{{ $t("app_bar.shortcut_menu") }}</span>
        </v-btn>

        <v-btn @click="showModalExport = true" data-tour="modal-export-open">
          <app-bar-icon>mdi-swap-vertical-bold</app-bar-icon>
          <span class="text-primary">{{ $t("app_bar.export_menu") }}</span>
        </v-btn>
      </div>

      <v-btn
        v-if="videoView && loggedIn"
        @click="showModalVideoUpload = true"
        :disabled="videoUploadStore.isUploading"
        data-tour="modal-video-upload-open"
      >
        <app-bar-icon>mdi-plus</app-bar-icon>
        <span class="text-primary">{{ $t("app_bar.video_upload_menu") }}</span>
      </v-btn>

      <v-btn
        v-if="videoView && loggedIn"
        @click="showModalBatchPlugin = true"
        :videoIds="selectedVideosIds"
        :disabled="selectedVideosIds.length == 0"
      >
        <app-bar-icon>mdi-plus</app-bar-icon>
        <span class="text-primary">{{ $t("app_bar.batch_plugin_menu") }}</span>
      </v-btn>

      <v-divider vertical inset class="mx-2" />

      <v-btn
        v-if="loggedIn"
        @click="showModalTutorial = true"
        icon
        density="compact"
        class="ml-2 mr-1"
      >
        <app-bar-icon>mdi-school</app-bar-icon>
        <v-badge
          v-if="tutorialStore.isTutorialRunning"
          :offset-y="-4"
          color="accent"
          floating
          dot
        />
        <v-tooltip
          v-if="tutorialStore.isTutorialRunning"
          activator="parent"
          location="bottom"
          class="tutorial-icon-tooltip"
          interactive
        >
          <div style="max-width: 400px">
            <div class="text-yellow">
              <strong>
                <v-icon small>mdi-arrow-right</v-icon>
                {{ tutorialStore.currentStepIdx }} / {{ tutorialStore.totalSteps }}</strong
              ><br />
              {{ tutorialStore.currentStepText }}
            </div>

            <v-divider class="my-3" style="width: 70%; margin: 0 auto" />

            <div>
              <strong
                >{{ tutorialStore.currentStepIdx + 1 }} / {{ tutorialStore.totalSteps }}</strong
              ><br />
              {{ tutorialStore.nextStepText }}
            </div>
          </div>
        </v-tooltip>
      </v-btn>

      <v-btn v-if="!loggedIn" @click="themeStore.toggle()" icon density="compact" class="mx-2">
        <app-bar-icon>mdi-theme-light-dark</app-bar-icon>
      </v-btn>

      <v-menu v-if="!loggedIn" location="bottom center">
        <template #activator="{ props }">
          <v-avatar v-bind="props" size="20" class="ml-2 mr-1">
            <v-img
              :src="
                languageStore.languages.find((lang) => lang.code === languageStore.currentLanguage)
                  ?.flag
              "
              contain
            />
          </v-avatar>
        </template>
        <v-list density="compact" class="py-0 mt-2" width="100px">
          <v-list-item
            v-for="lang in languageStore.languages"
            :key="lang.code"
            @click="languageStore.setLanguage(lang.code)"
          >
            <v-list-item-title class="text-center">{{ lang.label }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <UserMenu />
    </template>

    <ModalPlugin v-if="showModalPlugin" v-model="showModalPlugin" :videoIds="[videoId]" />
    <ModalHistory v-if="showModalHistory" v-model="showModalHistory" :pluginRuns="pluginRuns" />
    <ModalShortcut v-if="showModalShortcut" v-model="showModalShortcut" />
    <ModalExport v-if="showModalExport" v-model="showModalExport" />
    <ModalVideoUpload v-if="showModalVideoUpload" v-model="showModalVideoUpload" />
    <ModalPlugin
      v-if="showModalBatchPlugin"
      v-model="showModalBatchPlugin"
      :videoIds="selectedVideosIds"
    />
    <ModalTutorial v-if="showModalTutorial" v-model="showModalTutorial" />
  </v-app-bar>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import { useVideoStore } from "@/stores/video";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useTutorialStore } from "@/stores/tutorial";
import { useLanguageStore } from "@/stores/languages";
import { useVideoUploadStore } from "@/stores/video_upload";
import { useThemeStore } from "@/stores/theme";
import ModalHistory from "@/components/app/app-bar/ModalHistory.vue";
import ModalPlugin from "@/components/app/app-bar/ModalPlugin.vue";
import ModalShortcut from "@/components/app/app-bar/ModalShortcut.vue";
import ModalExport from "@/components/app/app-bar/ModalExport.vue";
import UserMenu from "@/components/user/UserMenu.vue";
import ModalTutorial from "@/components/app/app-bar/ModalTutorial.vue";
import ModalVideoUpload from "@/components/video/ModalVideoUpload.vue";

const route = useRoute();
const { t } = useI18n();

const playerStore = usePlayerStore();
const userStore = useUserStore();
const videoStore = useVideoStore();
const pluginRunStore = usePluginRunStore();
const tutorialStore = useTutorialStore();
const languageStore = useLanguageStore();
const videoUploadStore = useVideoUploadStore();
const themeStore = useThemeStore();

const loggedIn = computed(() => userStore.loggedIn);

const videoView = computed(() => route.name === "VideoView");
const analysisView = computed(() => route.name === "AnalysisView");
const termsOfUseView = computed(() => route.name === "TermsOfUseView");
const guidelinesView = computed(() => route.name === "GuidelinesView");

const showModalPlugin = ref(false);
const videoId = computed(() => playerStore.videoId);

const showModalHistory = ref(false);
const pluginRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .map((pluginRun) => {
      return {
        id: pluginRun.id,
        type: pluginName(pluginRun.type),
        date: pluginRun.date
          .replace("T", " ")
          .replace("Z", "")
          .substring(0, pluginRun.date.length - 8),
        progress: parseFloat(pluginRun.progress),
        status: pluginRun.status,
      };
    });
});
const numRunningPlugins = computed(() => {
  return pluginRuns.value.filter((e) => e.status !== "DONE" && e.status !== "ERROR").length;
});
const pluginName = (type) => {
  const typeMap = {
    aggregate_scalar: "modal.plugin.aggregation.plugin_name",
    audio_amp: "modal.plugin.audio_waveform.plugin_name",
    audio_freq: "modal.plugin.audio_frequency.plugin_name",
    audio_rms: "modal.plugin.audio_rms.plugin_name",
    clip: "modal.plugin.clip.plugin_name",
    x_clip: "modal.plugin.x_clip.plugin_name",
    clip_ontology: "modal.plugin.clip_ontology.plugin_name",
    color_analysis: "modal.plugin.color_analysis.plugin_name",
    color_brightness_analysis: "modal.plugin.color_brightness_analysis.plugin_name",
    facedetection: "modal.plugin.facedetection.plugin_name",
    face_clustering: "modal.plugin.face_clustering.plugin_name",
    deepface_emotion: "modal.plugin.faceemotion.plugin_name",
    insightface_facesize: "modal.plugin.facesize.plugin_name",
    insightface_identification: "modal.plugin.face_identification.plugin_name",
    blip_vqa: "modal.plugin.blip.plugin_name",
    place_identification: "modal.plugin.place_identification.plugin_name",
    places_classification: "modal.plugin.places_classification.plugin_name",
    place_clustering: "modal.plugin.place_clustering.plugin_name",
    whisper: "modal.plugin.whisper.plugin_name",
    shotdetection: "modal.plugin.shot_detection.plugin_name",
    shot_density: "modal.plugin.shot_density.plugin_name",
    shot_scalar_annotation: "modal.plugin.shot_scalar_annotation.plugin_name",
    shot_type_classification: "modal.plugin.shot_type_classification.plugin_name",
    thumbnail: "modal.plugin.thumbnail.plugin_name",
    bytetrack: "modal.plugin.bytetrack.plugin_name",
    calibration_static_dlt: "modal.plugin.calibration_static_dlt.plugin_name",
    posdata_convert: "modal.plugin.posdata_convert.plugin_name",
    kpi_computation: "modal.plugin.kpi_computation.plugin_name",
  };
  return t(typeMap[type] || type);
};

const showModalShortcut = ref(false);

const showModalExport = ref(false);

const showModalVideoUpload = ref(false);

const showModalBatchPlugin = ref(false);
const selectedVideosIds = computed(() => videoStore.selectedVideosIds);

const showModalTutorial = ref(false);
</script>

<style scoped>
.tutorial-icon-tooltip ::v-deep(.v-overlay__content) {
  background: rgb(var(--v-theme-primary));
  border-radius: 2px;
  font-size: 0.7rem;
  line-height: 1.3;
  overflow-wrap: anywhere;
  padding: 10px 15px;
  color: #fff;
}
</style>
