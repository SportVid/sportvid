<template>
  <v-dialog v-model="menu" width="700px">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props">
        <v-icon color="primary">mdi-history</v-icon>
        <v-badge 
          v-if="numRunningPlugins > 0" 
          color="accent" 
          :content="numRunningPlugins"
        >
          History
        </v-badge>
        <span v-else>
          History
        </span>
      </v-btn>
    </template>

    <v-data-table 
      :items-per-page="10" 
      :headers="headers" 
      :items="pluginRuns" 
      item-key="id" 
      class="elevation-1"
    >
      <template v-slot:item_status="{ value }">
        <v-chip :color="progressColor(value.status)"> {{ value.status }}</v-chip>
      </template>
      <template v-slot:item_progress="{ value }">
        <v-progress-linear :value="value.progress * 100" height="8">
        </v-progress-linear>
      </template>
    </v-data-table>
  </v-dialog>
</template>

<script>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import ModalPlugin from "@/components/ModalPlugin.vue";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";


export default {
  components: {
    ModalPlugin,
  },
  setup() {
    const menu = ref(false);
    const pluginRunStore = usePluginRunStore();
    const playerStore = usePlayerStore();
    const { t } = useI18n();

    const headers = [
      { text: 'Plugin Name', align: 'start', sortable: false, value: 'type' },
      { text: 'Date', value: 'date' },
      { text: 'Progress', value: 'progress' },
      { text: 'Status', value: 'status' }
    ];

    const progressColor = (status) => {
      if (status === "ERROR") return "red";
      if (status === "RUNNING") return "blue";
      if (status === "DONE") return "green";
      return "yellow";
    };

    const indeterminate = (status) => {
      return status === "QUEUED" || status === "WAITING";
    };

    const pluginStatus = (status) => {
      const statusMap = {
        UNKNOWN: "modal.plugin.status.unknown",
        ERROR: "modal.plugin.status.error",
        DONE: "modal.plugin.status.done",
        RUNNING: "modal.plugin.status.running",
        QUEUED: "modal.plugin.status.queued",
        WAITING: "modal.plugin.status.waiting",
      };
      return statusMap[status] ? t(statusMap[status]) : status;
    };

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
          date: pluginRun.date.replace("T", " ").replace("Z", "").substring(0, pluginRun.date.length - 5),
          progress: parseFloat(pluginRun.progress),
          status: pluginRun.status
        }));
    });

    const numRunningPlugins = computed(() => {
      return pluginRuns.value.filter((e) => e.status !== "DONE" && e.status !== "ERROR").length;
    });

    return {
      menu,
      headers,
      pluginRuns,
      numRunningPlugins,
      progressColor,
      indeterminate,
      pluginStatus,
      pluginName
    };
  }
};
</script>

<style scoped>
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
}

.text-overflow {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.plugin-name {
  font-weight: bold;
}

.v-menu__content .plugin-overview .v-btn:not(.accent) {
  justify-content: center;
}

.v-data-table .v-data-table-header tr th {
  font-size: 20px !important;
}
</style>
