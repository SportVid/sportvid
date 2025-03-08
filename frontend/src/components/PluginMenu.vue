<template>
  <div>
    <v-menu min-width="175">
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" @click="showModalPlugin = true">
          <v-icon color="primary">mdi-plus</v-icon>
          {{ $t("app_bar.plugin_menu") }}
        </v-btn>
      </template>
    </v-menu>

    <ModalPlugin v-model="showModalPlugin" :videoIds="[videoId]" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import ModalPlugin from "@/components/ModalPlugin.vue";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

const showModalPlugin = ref(false);

const playerStore = usePlayerStore();
const pluginRunStore = usePluginRunStore();
const pluginRunResultStore = usePluginRunResultStore();

const videoId = computed(() => playerStore.videoId);
const loggedIn = computed(() => playerStore.loggedIn);

const pluginRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .map((e) => ({
      ...e,
      date: Date.parse(e.date),
    }))
    .sort((a, b) => a.date - b.date);
});

const numRunningPlugins = computed(
  () => pluginRuns.value.filter((e) => e.status !== "DONE" && e.status !== "ERROR").length
);

const progressColor = (status) => {
  const colors = {
    ERROR: "red",
    RUNNING: "blue",
    DONE: "green",
  };
  return colors[status] || "yellow";
};

const indeterminate = (status) => ["QUEUED", "WAITING"].includes(status);

const pluginStatus = (status) => {
  const statusMap = {
    UNKNOWN: "modal.plugin.status.unknown",
    ERROR: "modal.plugin.status.error",
    DONE: "modal.plugin.status.done",
    RUNNING: "modal.plugin.status.running",
    QUEUED: "modal.plugin.status.queued",
    WAITING: "modal.plugin.status.waiting",
  };
  return statusMap[status] ? $t(statusMap[status]) : status;
};

const pluginName = (type) => {
  const pluginMap = {
    aggregate_scalar: "modal.plugin.aggregation.plugin_name",
    audio_amp: "modal.plugin.audio_waveform.plugin_name",
    audio_freq: "modal.plugin.audio_frequency.plugin_name",
    clip: "modal.plugin.clip.plugin_name",
    color_analysis: "modal.plugin.color_analysis.plugin_name",
    facedetection: "modal.plugin.facedetection.plugin_name",
    face_clustering: "modal.plugin.face_clustering.plugin_name",
    deepface_emotion: "modal.plugin.faceemotion.plugin_name",
    insightface_facesize: "modal.plugin.facesize.plugin_name",
    places_classification: "modal.plugin.places_classification.plugin_name",
    shotdetection: "modal.plugin.shot_detection.plugin_name",
    shot_density: "modal.plugin.shot_density.plugin_name",
    shot_type_classification: "modal.plugin.shot_type_classification.plugin_name",
    thumbnail: "modal.plugin.thumbnail.plugin_name",
  };
  return pluginMap[type] ? $t(pluginMap[type]) : type;
};
</script>

<style>
.v-menu__content .v-btn:not(.accent) {
  text-transform: capitalize;
  justify-content: left;
}

.v-btn:not(.v-btn--round).v-size--large {
  height: 48px;
}

.plugin-overview {
  background-color: rgb(255, 255, 255) !important;
  max-height: 500px;
  padding: 0;
  margin: 0;
}

.v-list-item__content.plugin-overview {
  min-width: 350px;
  max-width: 500px;
  letter-spacing: 0.0892857143em;
  overflow: auto;
  /* border-bottom: 1px solid #f5f5f5; */
}

.text-overflow {
  overflow: hidden;
  white-space: nowrap;
  /* Don't forget this one */
  text-overflow: ellipsis;
}

.plugin-name {
  font-weight: bold;
}

.v-menu__content .plugin-overview .v-btn:not(.accent) {
  justify-content: center;
}
</style>
