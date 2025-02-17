<template>
  <v-dialog v-model="dialog" width="750px">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.export.title") }}

        <v-spacer></v-spacer>

        <v-btn 
          icon 
          @click="dialog = false" 
          variant="plain" 
          color="grey"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text style="overflow: hidden;">
        <v-row>
          <v-col cols="4">
            <v-tabs 
              direction="vertical" 
              slider-color="primary"
              v-model="tab"
            >
              <v-tab 
                v-for="exportFormat in exportFormatsSorted" 
                :key="exportFormat.name"
                :value="exportFormat.name" 
              >
                <v-icon> {{ exportFormat.icon }} </v-icon>
                <span class="text-button ml-1">{{ exportFormat.name }}</span>
              </v-tab>
            </v-tabs>  
          </v-col>

          <v-divider vertical></v-divider>

          <v-col cols="7">  
            <v-card style="height: 35vh;  width: 470px;" flat>
              <v-tabs-window v-model="tab">
                <v-tabs-window-item 
                  v-for="exportFormat in exportFormatsSorted" 
                  :key="exportFormat.name"
                  :value="exportFormat.name"
                >
                    <v-card-title class="mb-0">{{ exportFormat.name }}</v-card-title>
                    
                    <v-card-text
                      style="flex-grow: 1; overflow-y: auto;"
                    >
                      <Parameters 
                        :videoIds="[videoId]" 
                        :parameters="exportFormat.parameters"
                        class="compact_parameters"
                      />
                    </v-card-text>
                </v-tabs-window-item>
              </v-tabs-window>
            </v-card>

            <v-row>
              <v-spacer></v-spacer>
              <v-btn 
                @click="downloadExport(
                  exportFormat.export, 
                  exportFormat.parameters
                )"
                class="mr-n12 mb-2"
              >
                {{ $t("modal.export.export") }}
              </v-btn>
            </v-row>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import Parameters from "./Parameters.vue";

export default {
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
  },
  setup(props, { emit }) {
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
      dialog.modelValue = false;
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

    return {
      dialog,
      exportFormatsSorted,
      videoId,
      downloadExport,
      tab
    };
  },
  components: { Parameters },
};
</script>

<style>
.compact-parameters {
  display: flex;
  flex-direction: column;
  gap: 4px; /* Abstand zwischen den Checkboxen */
}
</style>
