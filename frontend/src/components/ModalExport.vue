<template>
  <v-dialog v-model="dialog" max-width="90%">
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.export.title") }}

        <v-btn icon @click="dialog = false" absolute right>
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-tabs vertical class="tabs-left">
          <v-tab v-for="export_format in exportFormatsSorted" :key="export_format.name">
            <v-icon left> {{ export_format.icon }} </v-icon>
            <span class="text-button">{{ export_format.name }}</span>
          </v-tab>
          <v-tab-item v-for="export_format in exportFormatsSorted" :key="export_format.name">
            <v-card flat height="100%">
              <v-card-title>{{ export_format.name }} </v-card-title>
              <v-card-text>
                <Parameters :videoIds="[videoId]" :parameters="export_format.parameters" />
              </v-card-text>

              <v-card-actions class="pt-0">
                <v-btn @click="downloadExport(export_format.export, export_format.parameters)">
                  {{ $t("modal.export.export") }}
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-tab-item>
        </v-tabs>
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn @click="dialog = false">{{ $t("modal.export.close") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from "vue";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import Parameters from "./Parameters.vue";

export default {
  props: ["value"],
  setup(props, { emit }) {
    const videoStore = useVideoStore();
    const playerStore = usePlayerStore();

    const dialog = ref(false);

    const exportFormats = ref([
      {
        name: $t("modal.export.merged_csv.export_name"),
        icon: "mdi-file",
        export: "merged_csv",
        parameters: [
          {
            field: "checkbox",
            name: "merge_timeline",
            value: true,
            text: $t("modal.export.merged_csv.timeline_merge"),
          },
          {
            field: "checkbox",
            name: "use_timestamps",
            value: true,
            text: $t("modal.export.merged_csv.use_timestamps"),
          },
          {
            field: "checkbox",
            name: "use_seconds",
            value: true,
            text: $t("modal.export.merged_csv.use_seconds"),
          },
          {
            field: "checkbox",
            name: "include_category",
            value: true,
            text: $t("modal.export.merged_csv.include_category"),
          },
          {
            field: "checkbox",
            name: "split_places",
            value: true,
            text: $t("modal.export.merged_csv.split_places"),
          },
        ],
      },
      {
        name: $t("modal.export.individual_csv.export_name"),
        icon: "mdi-file",
        export: "individual_csv",
        parameters: [
          {
            field: "checkbox",
            name: "use_timestamps",
            value: true,
            text: $t("modal.export.individual_csv.use_timestamps"),
          },
          {
            field: "checkbox",
            name: "use_seconds",
            value: true,
            text: $t("modal.export.individual_csv.use_seconds"),
          },
          {
            field: "checkbox",
            name: "include_category",
            value: true,
            text: $t("modal.export.individual_csv.include_category"),
          },
        ],
      },
      {
        name: $t("modal.export.elan.export_name"),
        icon: "mdi-file",
        export: "elan",
        parameters: [
          {
            field: "select_timeline",
            name: "shot_timeline_id",
            text: $t("modal.plugin.shot_timeline_name"),
            hint: $t("modal.plugin.shot_timeline_hint"),
          },
          {
            field: "buttongroup",
            text: $t("modal.plugin.aggregation.method"),
            name: "aggregation",
            value: 0,
            buttons: [
              $t("modal.plugin.aggregation.max"),
              $t("modal.plugin.aggregation.min"),
              $t("modal.plugin.aggregation.mean"),
            ],
          },
        ],
      },
    ]);

    const videoId = computed(() => playerStore.videoId);

    const exportFormatsSorted = computed(() =>
      exportFormats.value.slice().sort((a, b) => a.name.localeCompare(b.name))
    );

    const downloadExport = async (format, parameters) => {
      const processedParams = parameters.map((e) => {
        if ("file" in e) {
          return { name: e.name, file: e.file };
        } else if (e.name === "shot_timeline_id") {
          return { name: e.name, value: e.value.timeline_ids[0] };
        } else {
          return { name: e.name, value: e.value };
        }
      });
      await videoStore.export({ format, parameters: processedParams });
      dialog.value = false;
    };

    watch(
      () => dialog.value,
      (newValue) => {
        emit("input", newValue);
      }
    );

    watch(
      () => props.value,
      (newValue) => {
        if (newValue) {
          dialog.value = true;
        }
      }
    );

    return {
      dialog,
      exportFormatsSorted,
      videoId,
      downloadExport,
    };
  },
  components: { Parameters },
};
</script>
