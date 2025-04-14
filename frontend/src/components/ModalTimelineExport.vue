<template>
  <v-dialog v-model="dialog" width="710px">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.timeline.export_result.title") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text style="overflow: hidden">
        <v-row>
          <v-col cols="3" class="ml-n3 mr-9">
            <v-tabs direction="vertical" slider-color="primary" v-model="tab" class="mr-n9">
              <v-tab
                v-for="exportFormat in exportFormatsSorted"
                :key="exportFormat.name"
                :value="exportFormat.name"
              >
                <v-icon>{{ exportFormat.icon }}</v-icon>
                <span class="text-button ml-1">{{ exportFormat.name }}</span>
              </v-tab>
            </v-tabs>
          </v-col>

          <v-divider vertical />

          <v-col style="width: 490px">
            <v-tabs-window v-model="tab">
              <v-tabs-window-item
                v-for="exportFormat in exportFormatsSorted"
                :key="exportFormat.name"
                :value="exportFormat.name"
              >
                <v-card style="height: 100px" flat>
                  <v-card-title class="mb-0">{{ exportFormat.name }}</v-card-title>

                  <v-card-text style="flex-grow: 1; overflow-y: auto">
                    {{ exportFormat.text }}
                  </v-card-text>
                </v-card>

                <v-row class="mt-n4 mb-1 mr-1">
                  <v-spacer />
                  <v-btn @click="downloadExport(exportFormat.export, exportFormat.parameters)">
                    {{ $t("modal.timeline.export_result.export") }}
                  </v-btn>
                </v-row>
              </v-tabs-window-item>
            </v-tabs-window>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useTimelineStore } from "@/stores/timeline";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import Parameters from "./Parameters.vue";

const props = defineProps({
  timeline: {
    type: Object,
    required: false,
  },
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);
const { t } = useI18n();

const tab = ref(null);

const exportFormats = ref([
  {
    name: t("modal.timeline.export_result.csv.export_name"),
    icon: "mdi-file",
    export: "csv",
    text: t("modal.timeline.export_result.csv.export_text"),
    parameters: [],
  },
]);

const exportFormatsSorted = computed(() =>
  exportFormats.value.slice(0).sort((a, b) => a.name.localeCompare(b.name))
);

const timelineStore = useTimelineStore();
const pluginRunResultStore = usePluginRunResultStore();

async function downloadExport() {
  const timeline = timelineStore.timelines[props.timeline];
  console.log("ExportTimeline", timeline);
  const result = pluginRunResultStore.get(timeline.plugin_run_result_id);
  console.log(result);

  if (result.type === "SCALAR") {
    let csv = "time,data\n";
    for (let i = 0; i < result.data.time.length; i++) {
      csv += `${result.data.time[i]},${result.data.y[i]}\n`;
    }

    const csvFile = new Blob([csv], { type: "text/csv" });
    const downloadLink = document.createElement("a");
    downloadLink.download = `${timeline.name}.csv`;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = "none";

    document.body.appendChild(downloadLink);
    downloadLink.click();
    dialog.value = false;
  }
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
