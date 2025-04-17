<template>
  <div>
    <v-btn @click="showModalHistory = true">
      <v-icon color="primary">mdi-history</v-icon>
      <v-badge v-if="numRunningPlugins > 0" color="accent" :content="numRunningPlugins" floating>
        {{ $t("app_bar.history_menu") }}
      </v-badge>
      <span v-else>
        {{ $t("app_bar.history_menu") }}
      </span>
    </v-btn>

    <ModalHistory v-if="showModalHistory" v-model="showModalHistory" :pluginRuns="pluginRuns" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import ModalHistory from "@/components/ModalHistory.vue";

const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();

const { t } = useI18n();

const showModalHistory = ref(false);

const pluginRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .map((pluginRun, index) => ({
      id: index,
      type: pluginName(pluginRun.type),
      date: pluginRun.date
        .replace("T", " ")
        .replace("Z", "")
        .substring(0, pluginRun.date.length - 8),
      progress: parseFloat(pluginRun.progress),
      status: pluginRun.status,
    }));
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
  };
  return t(typeMap[type] || type);
};
</script>
