<template>
  <v-dialog v-model="dialog" width="710px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.export.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
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
                <v-card style="height: 275px" flat>
                  <v-card-title class="mb-0">{{ exportFormat.name }}</v-card-title>

                  <v-card-text style="flex-grow: 1; overflow-y: auto">
                    <Parameters
                      :videoIds="[videoId]"
                      :parameters="exportFormat.parameters"
                      class="compact_parameters"
                    />
                  </v-card-text>
                </v-card>

                <v-row class="mt-n4 mb-1 mr-1">
                  <v-spacer />
                  <v-btn @click="downloadExport(exportFormat.export, exportFormat.parameters)">
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
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import Parameters from "./Parameters.vue";

import { useBboxesStore } from "@/stores/bboxes";
const bboxesStore = useBboxesStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits();

const videoStore = useVideoStore();
const playerStore = usePlayerStore();

const dialog = ref(props.modelValue);
const { t } = useI18n();

const tab = ref(null);

const exportFormats = ref([
  {
    name: t("modal.export.merged_csv.export_name"),
    icon: "mdi-file",
    export: "merged_csv",
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
    export: "individual_csv",
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
    export: "elan",
    parameters: [
      {
        field: "select_timeline",
        name: "shot_timeline_id",
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
    export: "positions_csv",
    parameters: [
      {
        field: "select_pos_data_team",
        name: "position_data_team",
        value: null,
        text: t("modal.plugin.position_data_name"),
        hint: t("modal.plugin.position_data_hint"),
      },
    ],
  },
]);

const videoId = computed(() => playerStore.videoId);

const exportFormatsSorted = computed(() =>
  exportFormats.value.slice().sort((a, b) => a.name.localeCompare(b.name))
);

const exportPositionsLocal = async ({ parameters = [] }) => {
  const selectedTeam = parameters.find((p) => p.name === "position_data_team")?.value;

  // const filteredPositions = bboxesStore.positionsNested.map((frame) =>
  //   frame.filter((player) => selectedTeam === "both" || player.team === selectedTeam)
  // );
  // const csvHeader = "frame,player,time,team,bbox_top,bbox_left,bbox_width,bbox_height,det_score\n";
  // const csvRows = filteredPositions
  //   .map((frame, frameIndex) =>
  //     frame
  //       .map((player, playerIndex) => {
  //         return `${frameIndex + 1},${playerIndex + 1},${player.time},${player.team},${player.bbox_top},${player.bbox_left},${player.bbox_width},${player.bbox_height},${player.det_score}`;
  //       })
  //       .join("\n")
  //   )
  //   .join("\n");
  const filteredPositions = bboxesStore.positionsFlat.filter(
    (player) => selectedTeam === "both" || player.team === selectedTeam
  );
  const csvHeader = "frame,player,time,team,y,x,w,h,det_score\n";
  const csvRows = filteredPositions
    .map((player) => {
      return `${player.image_id},${player.ref_id},${player.time},${player.team},${player.y},${player.x},${player.w},${player.h},${player.det_score}`;
    })
    .join("\n");

  const videoId = usePlayerStore().videoId;
  const csvContent = csvHeader + csvRows;
  const blob = new Blob([csvContent], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = window.URL.createObjectURL(blob);
  link.download = `${videoId}_positions_${selectedTeam}.csv`;
  link.click();
};

const downloadExport = async (format, parameters) => {
  // const processedParams = parameters.map((e) => {
  //   if ("file" in e) {
  //     return { name: e.name, file: e.file };
  //   } else if (e.name === "shot_timeline_id") {
  //     return { name: e.name, value: e.value.timeline_ids[0] };
  //   } else {
  //     return { name: e.name, value: e.value };
  //   }
  // });
  const processedParams = parameters.map((e) => {
    if ("file" in e) {
      return { name: e.name, file: e.file };
    } else if (e.name === "shot_timeline_id" && e.value?.timeline_ids?.length) {
      return { name: e.name, value: e.value.timeline_ids[0] };
    } else if (e.name === "position_data_team") {
      return { name: e.name, value: e.value };
    } else {
      return { name: e.name, value: e.value ?? null };
    }
  });
  if (format === "positions_csv") {
    await exportPositionsLocal({ parameters: processedParams });
  } else {
    await videoStore.exportVideo({ format, parameters: processedParams });
  }
  dialog.value = false;
};

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

<style scoped>
.compact-parameters {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
