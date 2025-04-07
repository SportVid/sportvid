<template>
  <v-dialog v-model="dialog" width="800">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.timeline.export_result.title") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text>
        <v-tabs vertical class="tabs-left">
          <v-tab v-for="exportFormat in exportFormatsSorted" :key="exportFormat.name">
            <v-icon left> {{ exportFormat.icon }} </v-icon>
            <span class="text-button">{{ exportFormat.name }}</span>
          </v-tab>
          <v-tab-item v-for="exportFormat in exportFormatsSorted" :key="exportFormat.name">
            <v-card flat height="100%">
              <v-card-title>{{ exportFormat.name }} </v-card-title>
              <v-card-text>
                <Parameters :parameters="exportFormat.parameters" />
              </v-card-text>

              <v-card-actions class="pt-0">
                <v-btn @click="downloadExport(exportFormat.export, exportFormat.parameters)">{{
                  $t("modal.timeline.export_result.export")
                }}</v-btn>
              </v-card-actions>
            </v-card>
          </v-tab-item>
        </v-tabs>
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn @click="dialog = false">{{ $t("modal.timeline.export_result.close") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from "vue";
import Parameters from "./Parameters.vue";
import { useTimelineStore } from "@/stores/timeline";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export default {
  props: {
    value: Boolean,
    timeline: String,
  },
  components: { Parameters },
  setup(props, { emit }) {
    const dialog = ref(false);

    const exportFormats = ref([
      {
        name: "CSV Export Name",
        icon: "mdi-file",
        export: "csv",
        parameters: [],
      },
    ]);

    const exportFormatsSorted = computed(() =>
      exportFormats.value.slice(0).sort((a, b) => a.name.localeCompare(b.name))
    );

    const timelineStore = useTimelineStore();
    const pluginRunResultStore = usePluginRunResultStore();

    async function downloadExport(format, parameters) {
      const timeline = timelineStore.get(props.timeline);
      const result = pluginRunResultStore.get(timeline.plugin_run_result_id);

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
        emit("input", value);
      }
    );

    watch(
      () => props.value,
      (value) => {
        if (value) {
          dialog.value = true;
        }
      }
    );

    return {
      dialog,
      exportFormatsSorted,
      downloadExport,
    };
  },
};
</script>

<style scoped>
.color-map {
  width: 100%;
  height: 100%;
  min-width: 200px;
  min-height: 30px;
  border: 1px solid gray;
}

.color-map-list {
  width: 100%;
}
</style>
