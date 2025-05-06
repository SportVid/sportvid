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

      <v-card-text class="mt-2" style="overflow-y: auto">
        <v-data-table
          color="primary"
          :items-per-page="10"
          :headers="headers"
          :items="props.pluginRuns"
          item-key="id"
          class="elevation-1 mb-3"
        >
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
import { ref, watch, watchEffect } from "vue";
import { useI18n } from "vue-i18n";

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

const dialog = ref(props.modelValue);

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
