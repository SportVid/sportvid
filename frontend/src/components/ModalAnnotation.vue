<template>
  <v-dialog v-model="dialog" width="700px">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.annotation.title") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="mt-2">
        <v-data-table
          :items-per-page="10"
          :headers="headers"
          :items="pluginRuns"
          item-key="id"
          @click:row="(_, item) => selectAnnotation(item)"
          class="elevation-1 mb-3"
        >
        </v-data-table>

        <v-row class="mt-6 mb-n2 justify-center">
          <v-btn class="mt-n2" @click="confirmSelection" :disabled="selectedAnnotation === null">
            {{ $t("modal.annotation.select") }}
          </v-btn>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";

const { t } = useI18n();
const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);

const headers = [
  { title: "Annotation", align: "start", key: "type" },
  { title: "Date", key: "date" },
];

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
  };
  return t(typeMap[type] || type);
};

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
        .substring(0, pluginRun.date.length - 5),
      progress: parseFloat(pluginRun.progress),
      status: pluginRun.status,
    }));
});

const selectedAnnotation = ref(null);

function selectAnnotation(item) {
  if (selectedAnnotation.value?.index === item.index) {
    selectedAnnotation.value = null;
  } else {
    selectedAnnotation.value = item;
  }
}

function confirmSelection() {
  if (selectedAnnotation.value) {
    console.log("Ausgewähltes Template:", selectedAnnotation.value);
  }
  dialog.value = false;
}

watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
  }
);

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      dialog.value = true;
    }
  }
);
</script>

<style></style>
