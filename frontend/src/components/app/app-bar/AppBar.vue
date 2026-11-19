<template>
  <v-app-bar>
    <template #prepend>
      <img :src="themeStore.isDark ? logoDark : logoLight" height="50" class="ml-1 mr-2" />
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
        <v-btn @click="showModalStatus = true" data-tour="modal-status-open">
          <app-bar-icon>mdi-format-list-checks</app-bar-icon>
          <span class="status-label">
            <span class="text-primary">{{ $t("app_bar.status_menu") }}</span>
            <span v-if="statusBadges.items.length" class="status-badge-stack">
              <span
                v-for="(badge, i) in statusBadges.items"
                :key="badge.key"
                class="status-badge"
                :class="`bg-${badge.color}`"
                :style="{ zIndex: 10 - i, opacity: STATUS_BADGE_OPACITY[i] }"
              >
                <v-icon v-if="badge.icon" size="11">{{ badge.icon }}</v-icon>
                <template v-else>{{ badge.text }}</template>
              </span>
            </span>
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
          <v-avatar v-bind="props" size="20" class="ml-2 mr-1" style="cursor: pointer">
            <v-img
              :src="
                languageStore.languages.find((lang) => lang.code === languageStore.currentLanguage)
                  ?.flag
              "
              contain
            />
          </v-avatar>
        </template>
        <v-card class="pa-2 mt-2">
          <v-btn-toggle
            :model-value="languageStore.currentLanguage"
            @update:model-value="languageStore.setLanguage($event)"
            color="primary"
            variant="outlined"
            divided
            mandatory
            density="compact"
          >
            <v-btn
              v-for="lang in languageStore.languages"
              :key="lang.code"
              :value="lang.code"
              size="small"
            >
              <v-avatar size="18">
                <v-img :src="lang.flag" contain />
              </v-avatar>
            </v-btn>
          </v-btn-toggle>
        </v-card>
      </v-menu>

      <UserMenu />
    </template>

    <ModalStatus
      v-if="showModalStatus"
      v-model="showModalStatus"
      :pluginRuns="pluginRuns"
      :canWrite="canWrite"
    />
    <ModalShortcut v-if="showModalShortcut" v-model="showModalShortcut" />
    <ModalExport v-if="showModalExport" v-model="showModalExport" />
    <ModalPlugin
      v-if="showModalBatchPlugin"
      v-model="showModalBatchPlugin"
      :videoIds="selectedVideosIds"
    />
    <ModalTutorial v-if="showModalTutorial" v-model="showModalTutorial" />
  </v-app-bar>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import logoLight from "@/assets/logo_dshs_marburg_light.png";
import logoDark from "@/assets/logo_dshs_marburg_dark.png";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import { useVideoStore } from "@/stores/video";
import { usePluginRunStore, isInternalPluginRun } from "@/stores/plugin_run";
import { useTutorialStore } from "@/stores/tutorial";
import { useLanguageStore } from "@/stores/languages";
import { useThemeStore } from "@/stores/theme";
import ModalStatus from "@/components/app/app-bar/ModalStatus.vue";
import ModalPlugin from "@/components/app/app-bar/ModalPlugin.vue";
import ModalShortcut from "@/components/app/app-bar/ModalShortcut.vue";
import ModalExport from "@/components/app/app-bar/ModalExport.vue";
import UserMenu from "@/components/user/UserMenu.vue";
import ModalTutorial from "@/components/app/app-bar/ModalTutorial.vue";

const route = useRoute();
const { t } = useI18n();

const playerStore = usePlayerStore();
const userStore = useUserStore();
const videoStore = useVideoStore();
const pluginRunStore = usePluginRunStore();
const tutorialStore = useTutorialStore();
const languageStore = useLanguageStore();
const themeStore = useThemeStore();

const loggedIn = computed(() => userStore.loggedIn);

const videoView = computed(() => route.name === "VideoView");
const analysisView = computed(() => route.name === "AnalysisView");
const termsOfUseView = computed(() => route.name === "TermsOfUseView");
const guidelinesView = computed(() => route.name === "GuidelinesView");

const showModalStatus = ref(false);
watch(
  () => pluginRunStore.openStatusModal,
  (val) => {
    if (val) {
      showModalStatus.value = true;
      pluginRunStore.openStatusModal = false;
    }
  }
);
const pluginRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    // Automatic internal runs (gallery thumbnail, camera motion classification) are not
    // user-facing analysis results -- see INTERNAL_PLUGIN_TYPES in stores/plugin_run.js.
    .filter((run) => !isInternalPluginRun(run))
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .map((pluginRun) => {
      return {
        id: pluginRun.id,
        type: pluginName(pluginRun.type),
        // the technical type -- `type` is the display name; ModalStatus labels the outcome with it
        plugin: pluginRun.type,
        failure_reason: pluginRun.failure_reason,
        outcome: pluginRun.outcome,
        date: pluginRun.date
          .replace("T", " ")
          .replace("Z", "")
          .substring(0, pluginRun.date.length - 8),
        progress: parseFloat(pluginRun.progress),
        eta_seconds: pluginRun.eta_seconds,
        status: pluginRun.status,
      };
    });
});
const isFinalStatus = (status) => status === "DONE" || status === "ERROR";
const numRunningPlugins = computed(() => {
  return pluginRuns.value.filter((e) => !isFinalStatus(e.status)).length;
});

// Runs that finished (DONE/ERROR) while the status modal was closed. They stay on the
// button as a check / exclamation mark until the modal is opened. Only transitions we
// actually observed count -- runs that were already finished when the video was loaded
// never show up here.
const unseenFinished = ref([]); // [{ id, status }], most recent first
const lastSeenStatus = new Map();
watch(
  pluginRuns,
  (runs) => {
    for (const run of runs) {
      const prev = lastSeenStatus.get(run.id);
      lastSeenStatus.set(run.id, run.status);
      if (prev === undefined || isFinalStatus(prev) || !isFinalStatus(run.status)) continue;
      if (showModalStatus.value) continue;
      unseenFinished.value = [
        { id: run.id, status: run.status },
        ...unseenFinished.value.filter((e) => e.id !== run.id),
      ];
    }
  },
  { immediate: true }
);
watch(showModalStatus, (open) => {
  if (open) unseenFinished.value = [];
});

// The first two badges are fully visible, the ones behind fade out. Anything beyond
// that is only in the status modal.
const STATUS_BADGE_OPACITY = [1, 1, 0.45];
const MAX_STATUS_BADGES = STATUS_BADGE_OPACITY.length;
const statusBadges = computed(() => {
  const items = [];
  if (numRunningPlugins.value > 0) {
    items.push({ key: "running", color: "accent", text: numRunningPlugins.value });
  }
  // Only runs of the current video (and still existing) -- same scope as the modal.
  // Errors go before successes so a failure is never hidden behind a later check mark.
  // A run that got through but left a hint (outcome.notices, e.g. a calibration without lens
  // correction) sits between the two, as a warning.
  const current = new Map(pluginRuns.value.map((r) => [r.id, r]));
  const finished = unseenFinished.value.filter((run) => current.has(run.id));
  const hasNotices = (run) => run.status === "DONE" && current.get(run.id).outcome?.notices?.length > 0;
  for (const run of finished.filter((r) => r.status === "ERROR")) {
    items.push({ key: run.id, color: "error", icon: "mdi-exclamation-thick" });
  }
  for (const run of finished.filter(hasNotices)) {
    items.push({ key: run.id, color: "warning", icon: "mdi-exclamation-thick" });
  }
  for (const run of finished.filter((r) => r.status === "DONE" && !hasNotices(r))) {
    items.push({ key: run.id, color: "success", icon: "mdi-check-bold" });
  }
  return { items: items.slice(0, MAX_STATUS_BADGES) };
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
    object_tracker: "modal.plugin.object_tracker.plugin_name",
    // Both are "the" camera calibration to the user (which one runs follows from the lens profile,
    // see usePluginParams.js); ModalStatus names the method that was actually used below it.
    calibration_static_dlt: "modal.plugin.calibration.plugin_name",
    calibration_lens_solve: "modal.plugin.calibration.plugin_name",
    posdata_convert: "modal.plugin.posdata_convert.plugin_name",
    kpi_computation: "modal.plugin.kpi_computation.plugin_name",
    team_clustering: "modal.plugin.team_clustering.plugin_name",
    osnet_reid: "modal.plugin.osnet_reid.plugin_name",
  };
  return t(typeMap[type] || type);
};

const showModalShortcut = ref(false);

const showModalExport = ref(false);

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const showModalBatchPlugin = ref(false);
const selectedVideosIds = computed(() => videoStore.selectedVideosIds);

const showModalTutorial = ref(false);
watch(
  () => tutorialStore.openTutorialModal,
  (val) => {
    if (val) {
      showModalTutorial.value = true;
      tutorialStore.openTutorialModal = false;
    }
  }
);
</script>

<style scoped>
.status-label {
  position: relative;
  display: inline-block;
}
.status-badge-stack {
  position: absolute;
  top: -9px;
  left: calc(100% - 8px);
  display: flex;
  pointer-events: none;
}
.status-badge {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  font-size: 0.65rem;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0;
  box-shadow: 0 0 0 1.5px rgb(var(--v-theme-surface));
}
/* 16px badge, 6px of each following badge peeks out. */
.status-badge + .status-badge {
  margin-left: -10px;
}.tutorial-icon-tooltip ::v-deep(.v-overlay__content) {
  background: rgb(var(--v-theme-primary));
  border-radius: 2px;
  font-size: 0.7rem;
  line-height: 1.3;
  overflow-wrap: anywhere;
  padding: 10px 15px;
  color: #fff;
}
</style>
