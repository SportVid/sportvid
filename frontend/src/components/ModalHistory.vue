<template>
  <v-dialog v-model="dialog" width="700px">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.history.title") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="mt-2" style="overflow-y: auto">
        <v-data-table
          :items-per-page="10"
          :headers="headers"
          :items="props.pluginRuns"
          item-key="id"
          class="elevation-1 mb-3"
        >
          <template v-slot:item.progress="{ index }">
            <v-progress-linear v-model="progressComputed[index]" height="8" color="primary" />
          </template>
          <template v-slot:item.status="{ value }">
            <v-chip :color="progressColor(value)" variant="flat">
              {{ value }}
            </v-chip>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, onMounted, watchEffect } from "vue";

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

const dialog = ref(props.modelValue);

const headers = [
  { title: "Plugin Name", align: "start", key: "type" },
  { title: "Date", key: "date" },
  { title: "Progress", key: "progress" },
  { title: "Status", key: "status" },
];

const progressColor = (status) => {
  if (status === "ERROR") return "red";
  if (status === "RUNNING") return "blue";
  if (status === "DONE") return "green";
  return "yellow";
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
