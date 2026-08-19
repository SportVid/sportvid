<template>
  <v-dialog v-model="dialog" width="900px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.status.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="mt-2 scrollable-content">
        <div class="mb-4">
          <div class="status-area mb-3 d-flex align-center" :class="`state-${posdataOverallState}`">
            <v-icon :color="stateColor(posdataOverallState)" size="28" class="mr-5">
              {{ stateIcon(posdataOverallState) }}
              <v-tooltip activator="parent" location="top">{{
                stateText(posdataOverallState, posdataAllTypes)
              }}</v-tooltip>
            </v-icon>

            <div class="flex-grow-1">
              <div class="font-weight-medium mb-2">{{ $t("modal.status.area.posdata") }}</div>

              <div class="d-flex align-center flex-wrap mb-2">
                <span class="text-caption text-medium-emphasis mr-3">{{
                  $t("modal.status.variant.auto")
                }}</span>
                <div class="d-flex align-center mr-4">
                  <v-icon :color="stateColor(playerTrackingState)" size="18" class="mr-1">
                    {{ stateIcon(playerTrackingState) }}
                  </v-icon>
                  <span class="text-caption">{{ $t("modal.status.source.player_tracking") }}</span>
                </div>
                <div class="d-flex align-center mr-4">
                  <v-icon :color="stateColor(dltState)" size="18" class="mr-1">
                    {{ stateIcon(dltState) }}
                  </v-icon>
                  <span class="text-caption">{{ $t("modal.status.source.dlt") }}</span>
                </div>
                <div class="d-flex align-center">
                  <v-icon :color="stateColor(objectTrackingState)" size="18" class="mr-1">
                    {{ stateIcon(objectTrackingState) }}
                    <v-tooltip activator="parent" location="top">{{
                      $t("modal.status.optional")
                    }}</v-tooltip>
                  </v-icon>
                  <span class="text-caption text-medium-emphasis">{{
                    $t("modal.status.source.object_tracking")
                  }}</span>
                </div>
              </div>

              <div class="d-flex align-center mt-n2 mb-0">
                <v-divider class="flex-grow-1" />
                <span class="text-caption text-medium-emphasis mx-2">{{
                  $t("modal.status.variant.or")
                }}</span>
                <v-divider class="flex-grow-1" />
              </div>

              <div class="d-flex align-center">
                <span class="text-caption text-medium-emphasis mr-3">{{
                  $t("modal.status.variant.manual")
                }}</span>
                <div class="d-flex align-center">
                  <v-icon :color="stateColor(uploadState)" size="18" class="mr-1">
                    {{ stateIcon(uploadState) }}
                  </v-icon>
                  <span class="text-caption">{{ $t("modal.status.source.upload") }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="status-area d-flex align-center" :class="`state-${kpiState}`">
            <v-icon :color="stateColor(kpiState)" size="28" class="mr-5">
              {{ stateIcon(kpiState) }}
              <v-tooltip activator="parent" location="top">{{
                stateText(kpiState, kpiTypes)
              }}</v-tooltip>
            </v-icon>

            <div>
              <div class="font-weight-medium">{{ $t("modal.status.area.kpi") }}</div>
              <div v-if="!posdataAvailable" class="text-caption text-medium-emphasis mt-1">
                {{ $t("modal.status.kpi_requires_posdata") }}
              </div>
            </div>
          </div>

          <div class="status-area mt-3 d-flex align-center" :class="`state-${transcriptState}`">
            <v-icon :color="stateColor(transcriptState)" size="28" class="mr-5">
              {{ stateIcon(transcriptState) }}
              <v-tooltip activator="parent" location="top">{{
                stateText(transcriptState, transcriptTypes)
              }}</v-tooltip>
            </v-icon>

            <div class="font-weight-medium">{{ $t("modal.status.area.transcript") }}</div>
          </div>
        </div>

        <v-divider class="mb-4" />

        <v-data-table
          data-tour="status-table"
          color="primary"
          hide-default-footer
          :headers="headers"
          :items="props.pluginRuns"
          item-key="id"
          class="mb-3 status-table"
        >
          <template #item.date="{ item }">
            {{ formatLocalDate(item.date) }}
          </template>
          <template #item.progress="{ index }">
            <v-progress-linear
              v-model="progressComputed[index]"
              height="8"
              color="primary"
              rounded
            />
          </template>
          <template #item.status="{ value }">
            <v-chip :color="progressColor(value)" variant="flat">
              {{ getStatusText(value) }}
            </v-chip>
          </template>
        </v-data-table>

        <v-expansion-panels v-if="props.canWrite" data-tour="status-delete-panel">
          <v-expansion-panel>
            <v-expansion-panel-title class="delete-panel-title">{{
              $t("modal.status.delete.title")
            }}</v-expansion-panel-title>
            <v-expansion-panel-text class="my-2">
              <v-row>
                <v-col cols="12" md="6">
                  <v-sheet class="pa-2 sheet-color" elevation="2" rounded>
                    <v-btn
                      block
                      color="error"
                      @click="
                        pluginRunStore.deletePlugins({ pluginRuns: props.pluginRuns, all: true })
                      "
                    >
                      {{ $t("modal.status.delete.all") }}
                    </v-btn>
                  </v-sheet>
                </v-col>

                <v-col cols="12" md="6">
                  <v-sheet class="pa-2 sheet-color" elevation="2" rounded>
                    <v-btn
                      block
                      color="error"
                      :disabled="!props.pluginRuns.length"
                      @click="
                        pluginRunStore.deletePlugins({
                          pluginRuns: props.pluginRuns,
                          videoId: playerStore.videoId,
                        })
                      "
                    >
                      {{ $t("modal.status.delete.video") }}
                    </v-btn>
                  </v-sheet>
                </v-col>

                <v-col cols="12" md="6">
                  <v-sheet class="pa-2 sheet-color" elevation="2" rounded>
                    <v-select
                      v-model="selectedPlugin"
                      :items="pluginTypes"
                      label="Select plugin"
                      item-title="type"
                      item-value="id"
                      variant="solo-filled"
                      density="comfortable"
                      :disabled="!props.pluginRuns.length"
                      chips
                    />
                    <v-btn
                      block
                      color="error"
                      class="mt-n2"
                      :disabled="!props.pluginRuns.length"
                      @click="
                        pluginRunStore.deletePlugins({
                          pluginRuns: props.pluginRuns,
                          plugin: selectedPlugin,
                        })
                      "
                    >
                      {{ $t("modal.status.delete.plugin") }}
                    </v-btn>
                  </v-sheet>
                </v-col>

                <v-col cols="12" md="6">
                  <v-sheet class="pa-2 sheet-color" elevation="2" rounded>
                    <v-select
                      v-model="selectedIds"
                      :items="props.pluginRuns"
                      label="Select individual plugin runs"
                      item-title="type"
                      item-value="id"
                      multiple
                      variant="solo-filled"
                      density="comfortable"
                      :disabled="!props.pluginRuns.length"
                    >
                      <template v-slot:selection="{ item, index }">
                        <v-chip v-if="index < 2" :text="item.title"></v-chip>

                        <span v-if="index === 2" class="text-grey text-caption align-self-center">
                          (+{{ selectedIds.length - 2 }} others)
                        </span>
                      </template>
                    </v-select>
                    <v-btn
                      class="mt-n2"
                      block
                      color="error"
                      :disabled="!props.pluginRuns.length"
                      @click="
                        pluginRunStore.deletePlugins({
                          pluginRuns: props.pluginRuns,
                          ids: selectedIds,
                        })
                      "
                    >
                      {{ $t("modal.status.delete.selected") }}
                    </v-btn>
                  </v-sheet>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch, watchEffect, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { usePositionDataStatus } from "@/composables/usePositionDataStatus";

const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();
const pluginRunResultStore = usePluginRunResultStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  pluginRuns: {
    type: Array,
    default: () => [],
  },
  canWrite: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits();

const { t } = useI18n();

const pluginTypes = computed(() => [...new Set(props.pluginRuns.map((p) => p.type))]);
const selectedPlugin = ref(null);
const selectedIds = ref([]);
watch(
  () => props.pluginRuns,
  () => {
    selectedPlugin.value = null;
    selectedIds.value = [];
  }
);

const dialog = ref(props.modelValue);
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

const headers = [
  { title: t("modal.status.plugin_name"), align: "start", key: "type", width: "40%" },
  { title: t("modal.status.date"), align: "start", key: "date", width: "25%" },
  { title: t("modal.status.progress"), align: "start", key: "progress", width: "20%" },
  { title: t("modal.status.status"), align: "start", key: "status", width: "15%" },
];

const progressColor = (status) => {
  if (status === "ERROR") return "red";
  if (status === "RUNNING") return "blue";
  if (status === "DONE") return "green";
  return "yellow";
};

const getStatusText = (status) => {
  return t(`modal.plugin.status.${status.toLowerCase()}`);
};

// Status overview (read-only), derived from raw plugin runs / position data -- shared with
// PositionDataMenu's disabled-Select tooltip, see usePositionDataStatus.
const {
  playerTrackingState,
  objectTrackingState,
  dltState,
  uploadState,
  kpiState,
  transcriptState,
  posdataOverallState,
  posdataAvailable,
  maxProgress,
} = usePositionDataStatus();

const stateColor = (state) => {
  if (state === "done") return progressColor("DONE");
  if (state === "running") return progressColor("RUNNING");
  if (state === "error") return progressColor("ERROR");
  return "grey";
};

const stateIcon = (state) => {
  const icons = {
    done: "mdi-checkbox-marked-circle-outline",
    running: "mdi-progress-clock",
    error: "mdi-alert-circle-outline",
    none: "mdi-checkbox-blank-circle-outline",
  };
  return icons[state] || icons.none;
};

const stateText = (state, types = null) => {
  const key = state === "done" ? "available" : state;
  let text = t(`modal.status.state.${key}`);
  if (state === "running" && types) {
    const progress = maxProgress(types);
    if (progress !== null) {
      text += ` (${progress}%)`;
    }
  }
  return text;
};

// Just the type lists the template needs for stateText()'s progress lookup -- the actual
// state derivation lives in usePositionDataStatus now.
const posdataAllTypes = ["bytetrack", "object_tracker", "calibration_static_dlt", "posdata_convert"];
const kpiTypes = ["kpi_computation"];
const transcriptTypes = ["whisper"];

// Cheap call (no add_results) so tracker runs can be classified as player- vs.
// object(ball)-tracking via their result name (see usePositionDataStatus's isBallTrackerRun).
onMounted(() => {
  pluginRunResultStore.fetchForVideo({ videoId: playerStore.videoId });
});

const progressComputed = ref([]);
watchEffect(() => {
  progressComputed.value = props.pluginRuns.map((run) => run.progress * 100);
});

const formatLocalDate = (dateString) => {
  if (!dateString) return "";

  let isoString = dateString.replace(" ", "T");
  if (!isoString.endsWith("Z")) {
    isoString += "Z";
  }
  const date = new Date(isoString);
  const isoDate = date.toISOString().slice(0, 10);
  const localTime = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return `${isoDate} ${localTime}`;
};
</script>

<style scoped>
.scrollable-content {
  max-height: 500px;
  overflow-y: auto;
}

.sheet-color {
  background-color: rgba(var(--v-theme-error), 0.3);
}

.status-area {
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  background-color: rgba(var(--v-theme-on-surface), 0.035);
}

.status-table {
  border-radius: 8px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  background-color: rgba(var(--v-theme-on-surface), 0.035) !important;
}

.status-area.state-done {
  border-color: rgba(76, 175, 80, 0.4);
  background-color: rgba(76, 175, 80, 0.12);
}

.status-area.state-running {
  border-color: rgba(33, 150, 243, 0.4);
  background-color: rgba(33, 150, 243, 0.12);
}

.status-area.state-error {
  border-color: rgba(244, 67, 54, 0.4);
  background-color: rgba(244, 67, 54, 0.12);
}

.delete-panel-title {
  background-color: rgba(var(--v-theme-error), 0.1);
}

.delete-panel {
  border: 2px solid rgba(var(--v-theme-error), 0.5);
  border-radius: 8px;
}
</style>
