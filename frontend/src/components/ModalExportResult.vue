<template>
  <v-dialog v-model="dialog" max-width="1000">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" text block large>
        <v-icon left>mdi-swap-vertical</v-icon>
        {{ $t("modal.timeline.export_result.link") }}
      </v-btn>
    </template>
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.timeline.export_result.title") }}

        <v-btn icon @click="dialog = false" absolute top right>
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-tabs vertical class="tabs-left">
          <v-tab
            v-for="export_format in export_formats_sorted"
            :key="export_format.name"
          >
            <v-icon left> {{ export_format.icon }} </v-icon>
            <span class="text-button">{{ export_format.name }}</span>
          </v-tab>
          <v-tab-item
            v-for="export_format in export_formats_sorted"
            :key="export_format.name"
          >
            <v-card flat height="100%">
              <v-card-title>{{ export_format.name }} </v-card-title>
              <v-card-text>
                <Parameters :parameters="export_format.parameters" />
              </v-card-text>

              <v-card-actions class="pt-0">
                <v-btn
                  @click="
                    downloadExport(
                      export_format.export,
                      export_format.parameters
                    )
                  "
                  >{{ $t("modal.timeline.export_result.export") }}</v-btn
                >
              </v-card-actions>
            </v-card>
          </v-tab-item>
        </v-tabs>
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn @click="dialog = false">{{
          $t("modal.timeline.export_result.close")
        }}</v-btn>
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
