<template>
  <v-dialog v-model="dialog" width="900px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.history.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="mt-2 scrollable-content">
        <v-expansion-panels>
          <v-expansion-panel>
            <v-expansion-panel-title color="error">{{
              $t("modal.history.delete.title")
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
                      {{ $t("modal.history.delete.all") }}
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
                      {{ $t("modal.history.delete.video") }}
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
                    >
                      <template v-slot:selection="{ item }">
                        <v-chip :text="item.title" />
                      </template>
                    </v-select>
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
                      {{ $t("modal.history.delete.plugin") }}
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
                      {{ $t("modal.history.delete.selected") }}
                    </v-btn>
                  </v-sheet>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <v-data-table
          color="primary"
          hide-default-footer
          :headers="headers"
          :items="props.pluginRuns"
          item-key="id"
          class="elevation-2 mb-3 mt-4"
        >
          <template #item.date="{ item }">
            {{ formatLocalDate(item.date) }}
          </template>
          <template #item.progress="{ index }">
            <v-progress-linear v-model="progressComputed[index]" height="8" color="primary" />
          </template>
          <template #item.status="{ value }">
            <v-chip :color="progressColor(value)" variant="flat">
              {{ getStatusText(value) }}
            </v-chip>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch, watchEffect } from "vue";
import { useI18n } from "vue-i18n";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePlayerStore } from "@/stores/player";

const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  pluginRuns: {
    type: Array,
    default: () => [],
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
  { title: t("modal.history.plugin_name"), align: "start", key: "type", width: "40%" },
  { title: t("modal.history.date"), align: "start", key: "date", width: "25%" },
  { title: t("modal.history.progress"), align: "start", key: "progress", width: "20%" },
  { title: t("modal.history.status"), align: "start", key: "status", width: "15%" },
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
</style>
