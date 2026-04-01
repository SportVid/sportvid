<template>
  <v-dialog v-model="dialog" width="750px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.export.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text>
        <v-row>
          <v-col cols="4" class="ml-n2 mr-2">
            <v-tabs direction="vertical" slider-color="primary" v-model="tab">
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

          <v-col cols="8">
            <v-tabs-window v-model="tab">
              <v-tabs-window-item
                v-for="exportFormat in exportFormatsSorted"
                :key="exportFormat.name"
                :value="exportFormat.name"
              >
                <v-card flat>
                  <v-card-title class="mb-0">{{ exportFormat.name }}</v-card-title>

                  <v-card-text style="height: 290px; overflow-y: auto">
                    <Parameters
                      :videoIds="[playerStore.videoId]"
                      :parameters="exportFormat.parameters"
                    />
                  </v-card-text>
                </v-card>

                <v-row class="mt-2 mb-1 mr-1">
                  <v-spacer />
                  <v-btn
                    @click="
                      downloadExport(
                        exportFormat.format,
                        exportFormat.parameters,
                        playerStore.videoId
                      )
                    "
                    :disabled="isExportDisabled(exportFormat)"
                  >
                    {{ $t("button.export") }}
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
import { useExportStore } from "@/stores/export";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import Parameters from "./Parameters.vue";

const exportStore = useExportStore();
const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();

const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits();

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

const tab = ref(null);

const allFrameKeys = topViewStore.sortedFrameKeys;

const exportFormats = ref([
  {
    name: t("modal.export.merged_csv.export_name"),
    icon: "mdi-file",
    format: "merged_csv",
    parameters: [
      {
        field: "checkbox",
        name: "merge_timeline",
        value: true,
        text: t("modal.export.merged_csv.timeline_merge"),
      },
      {
        field: "checkbox",
        name: "use_timestamps",
        value: true,
        text: t("modal.export.merged_csv.use_timestamps"),
      },
      {
        field: "checkbox",
        name: "use_seconds",
        value: true,
        text: t("modal.export.merged_csv.use_seconds"),
      },
      {
        field: "checkbox",
        name: "include_category",
        value: true,
        text: t("modal.export.merged_csv.include_category"),
      },
      {
        field: "checkbox",
        name: "split_places",
        value: true,
        text: t("modal.export.merged_csv.split_places"),
      },
    ],
  },
  {
    name: t("modal.export.individual_csv.export_name"),
    icon: "mdi-file",
    format: "individual_csv",
    parameters: [
      {
        field: "checkbox",
        name: "use_timestamps",
        value: true,
        text: t("modal.export.individual_csv.use_timestamps"),
      },
      {
        field: "checkbox",
        name: "use_seconds",
        value: true,
        text: t("modal.export.individual_csv.use_seconds"),
      },
      {
        field: "checkbox",
        name: "include_category",
        value: true,
        text: t("modal.export.individual_csv.include_category"),
      },
    ],
  },
  {
    name: t("modal.export.elan.export_name"),
    icon: "mdi-file",
    format: "elan",
    parameters: [
      {
        field: "select_timeline",
        name: "shot_timeline_id",
        value: null,
        text: t("modal.plugin.shot_timeline_name"),
        hint: t("modal.plugin.shot_timeline_hint"),
      },
      {
        field: "buttongroup",
        text: t("modal.plugin.aggregation.method"),
        name: "aggregation",
        value: 0,
        buttons: [
          t("modal.plugin.aggregation.max"),
          t("modal.plugin.aggregation.min"),
          t("modal.plugin.aggregation.mean"),
        ],
      },
    ],
  },
  {
    name: t("modal.export.position_data.export_name"),
    icon: "mdi-file",
    format: "positions_csv",
    parameters: [
      {
        field: "select_position_data_team",
        name: "position_data_team",
        value: null,
        text: t("modal.plugin.position_data_team_name"),
        hint: t("modal.plugin.position_data_team_hint"),
      },
      {
        field: "select_position_data_attribute",
        name: "position_data_attribute",
        value: [],
        text: t("modal.plugin.position_data_attribute_name"),
        hint: t("modal.plugin.position_data_attribute_hint"),
      },
      {
        field: "select_kpi_frame",
        name: "kpi_start_frame",
        value: allFrameKeys[0],
        items: allFrameKeys.slice(0, -1),
        text: t("modal.plugin.kpi_start_frame_name"),
      },
      {
        field: "select_kpi_frame",
        name: "kpi_end_frame",
        value: allFrameKeys[allFrameKeys.length - 1],
        items: allFrameKeys.slice(1),
        text: t("modal.plugin.kpi_end_frame_name"),
      },
    ],
  },
  {
    name: t("modal.export.kpi.export_name"),
    icon: "mdi-file",
    format: "kpi_csv",
    parameters: [
      {
        field: "select_kpi_team",
        name: "kpi_team",
        value: [],
        text: t("modal.plugin.kpi_team_name"),
        hint: t("modal.plugin.kpi_team_hint"),
      },
      {
        field: "select_kpi_names",
        name: "kpi_names",
        value: [],
        text: t("modal.plugin.kpi_names_name"),
        hint: t("modal.plugin.kpi_names_hint"),
      },
      {
        field: "select_kpi_attribute",
        name: "kpi_attribute",
        value: [],
        text: t("modal.plugin.kpi_attribute_name"),
        hint: t("modal.plugin.kpi_attribute_hint"),
      },
      {
        field: "select_kpi_frame",
        name: "kpi_start_frame",
        value: allFrameKeys[0],
        items: allFrameKeys.slice(0, -1),
        text: t("modal.plugin.kpi_start_frame_name"),
      },
      {
        field: "select_kpi_frame",
        name: "kpi_end_frame",
        value: allFrameKeys[allFrameKeys.length - 1],
        items: allFrameKeys.slice(1),
        text: t("modal.plugin.kpi_end_frame_name"),
      },
    ],
  },
  {
    name: t("modal.export.kpi_aggregated.export_name"),
    icon: "mdi-file",
    format: "kpi_aggregated_csv",
    parameters: [
      {
        field: "select_kpi_team",
        name: "kpi_team",
        value: [],
        text: t("modal.plugin.kpi_team_name"),
        hint: t("modal.plugin.kpi_team_hint"),
      },
      {
        field: "select_kpi_names_aggregated",
        name: "kpi_names",
        value: [],
        text: t("modal.plugin.kpi_names_name"),
        hint: t("modal.plugin.kpi_names_hint"),
      },
      {
        field: "select_kpi_attribute",
        name: "kpi_attribute",
        value: [],
        text: t("modal.plugin.kpi_attribute_name"),
        hint: t("modal.plugin.kpi_aggregated_attribute_hint"),
      },
      {
        field: "select_kpi_frame",
        name: "kpi_start_frame",
        value: allFrameKeys[0],
        items: allFrameKeys.slice(0, -1),
        text: t("modal.plugin.kpi_start_frame_name"),
      },
      {
        field: "select_kpi_frame",
        name: "kpi_end_frame",
        value: allFrameKeys[allFrameKeys.length - 1],
        items: allFrameKeys.slice(1),
        text: t("modal.plugin.kpi_end_frame_name"),
      },
    ],
  },
]);

const exportFormatsSorted = computed(() =>
  exportFormats.value.slice().sort((a, b) => a.name.localeCompare(b.name))
);

const downloadExport = async (format, parameters, videoId) => {
  const processedParams = parameters.map((e) => {
    if ("file" in e) {
      return { name: e.name, file: e.file };
    } else if (e.name === "shot_timeline_id" && e.value?.timeline_ids?.length) {
      return { name: e.name, value: e.value.timeline_ids[0] };
    } else if (
      e.name === "position_data_team" ||
      e.name === "position_data_attribute" ||
      e.name === "kpi_team" ||
      e.name === "kpi_names" ||
      e.name === "kpi_attribute"
    ) {
      return { name: e.name, value: [...e.value] };
    } else {
      return { name: e.name, value: e.value ?? null };
    }
  });

  await exportStore.exportData(format, processedParams, videoId);
  dialog.value = false;
};

const isExportDisabled = (exportFormat) => {
  const selectParams = exportFormat.parameters.filter((p) => p.field.startsWith("select"));
  if (!selectParams.length) return false;

  const emptyRequired = selectParams.some((p) => {
    if (p.name === "kpi_start_frame" || p.name === "kpi_end_frame") {
      return false;
    }
    if (p.name === "position_data_attribute" || p.name === "kpi_attribute") {
      return false;
    }
    return !p.value || (Array.isArray(p.value) && p.value.length === 0);
  });

  const startParam = selectParams.find((p) => p.name === "kpi_start_frame");
  const endParam = selectParams.find((p) => p.name === "kpi_end_frame");
  const invalidFrames =
    startParam && endParam && startParam.value != null && endParam.value != null
      ? startParam.value >= endParam.value
      : false;

  return emptyRequired || invalidFrames;
};
</script>

<style scoped>
.compact-parameters {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
