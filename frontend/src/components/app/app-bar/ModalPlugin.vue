<template>
  <v-dialog v-model="dialog" width="80%" style="height: 85vh">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.plugin.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="overflow: hidden">
        <v-row>
          <v-col cols="3" class="ml-n3" data-tour="plugin-panel">
            <v-text-field
              v-model="searchPlugin"
              :label="$t('modal.plugin.search')"
              class="searchField"
              variant="solo-filled"
              hide-details
              clearable
              clear-icon="mdi-close-circle-outline"
            />

            <v-treeview
              v-model="activeNode"
              class="mt-2 pr-4"
              fluid
              open-on-click
              :items="pluginsSorted"
              :search="searchPlugin"
              v-model:opened="opened"
              item-value="id"
              item-title="name"
              style="cursor: pointer; overflow-y: auto; height: 55vh"
            >
              <template #prepend="{ item }">
                <v-icon v-if="!item.children || item.children.length === 0">
                  {{ item.icon }}
                </v-icon>
              </template>
              <template #item="{ item, props: itemProps }">
                <v-list-item
                  v-bind="itemProps"
                  :data-tour="
                    item.id === 703
                      ? 'plugin-kpi-computation'
                      : item.id === 701
                      ? 'plugin-bytetrack'
                      : item.id === 702
                      ? 'plugin-calibration-dlt'
                      : undefined
                  "
                />
              </template>
            </v-treeview>
          </v-col>

          <v-divider vertical />

          <v-col cols="9" data-tour="plugin-details">
            <div
              v-if="!selected"
              class="text-h4 text-grey font-weight-light"
              style="display: flex; justify-content: center; align-items: center; height: 60vh"
            >
              {{ $t("modal.plugin.search") }}
            </div>

            <v-card v-else :key="selected.id" class="mx-auto" style="height: 60vh" flat>
              <v-card-title class="mb-0">{{ selected.name }}</v-card-title>

              <v-card-text style="flex-grow: 1; overflow-y: auto; max-height: 50vh">
                <div style="padding-bottom: 2em" v-html="selected.description" />

                <Parameters
                  :parameters="selected.parameters"
                  :videoIds="videoIds"
                  @create-calibration="onCreateCalibration"
                  @select-calibration="onSelectCalibration"
                />

                <v-expansion-panels
                  v-if="selected.optional_parameters && selected.optional_parameters.length > 0"
                  class="mt-4"
                  data-tour="kpi-advanced-options"
                >
                  <v-expansion-panel>
                    <v-expansion-panel-title expand-icon="mdi-menu-down">
                      {{ $t("modal.plugin.advanced_options") }}
                    </v-expansion-panel-title>

                    <v-expansion-panel-text>
                      <Parameters :parameters="selected.optional_parameters" :videoIds="videoIds" />
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-card-text>
            </v-card>

            <v-row>
              <v-spacer />
              <v-btn
                v-if="selected"
                @click="
                  runPlugin(selected.plugin, selected.parameters, selected.optional_parameters)
                "
                data-tour="kpi-run-plugin"
              >
                {{ $t("button.run_plugin") }}
              </v-btn>
            </v-row>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>

  <ModalCalibrationAssetCreate v-if="showCalibrationCreate" v-model="showCalibrationCreate" />
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePlayerStore } from "@/stores/player";
import { useTutorialStore } from "@/stores/tutorial";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { usePositionDataStore } from "@/stores/position_data";
import Parameters from "./Parameters.vue";
import ModalCalibrationAssetCreate from "@/components/calibration-asset/ModalCalibrationAssetCreate.vue";

const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();
const positionDataStore = usePositionDataStore();
const tutorialStore = useTutorialStore();
const calibrationAssetStore = useCalibrationAssetStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  videoIds: Array,
});

const emit = defineEmits();

const { t } = useI18n();
const dialog = ref(props.modelValue);
const searchPlugin = ref(null);
const activeNode = ref([]);
const showCalibrationCreate = ref(false);

const onCreateCalibration = () => {
  showCalibrationCreate.value = true;
};

const onSelectCalibration = () => {
  dialog.value = false;
  calibrationAssetStore.calibrationMode = true;
};

watch(showCalibrationCreate, (newVal, oldVal) => {
  if (oldVal && !newVal && calibrationAssetStore.calibrationAssetObjects.length > 0) {
    dialog.value = false;
    calibrationAssetStore.calibrationMode = true;
  }
});
const ALL_OBJECT_TRACKER_DETECTOR_ITEMS = [
  { title: "YOLOX", value: "yolox" },
  { title: "YOLOv10 (Ultralytics)", value: "yolo10" },
  { title: "YOLOv11 (Ultralytics)", value: "yolo11" },
  { title: "YOLOv12 (Ultralytics)", value: "yolo12" },
  { title: "YOLOv26 (Ultralytics)", value: "yolo26" },
  { title: "RF-DETR", value: "rfdetr" },
  { title: "RT-DETR", value: "rtdetr" },
];
const BALL_OBJECT_TRACKER_DETECTOR_ITEMS = ALL_OBJECT_TRACKER_DETECTOR_ITEMS.filter((d) =>
  ["yolo11", "yolo12", "rfdetr"].includes(d.value)
);

const plugins = ref([
  // {
  //   id: 1,
  //   name: t("modal.plugin.groups.audio"),
  //   children: [
  //     {
  //       name: t("modal.plugin.audio_rms.plugin_name"),
  //       description: t("modal.plugin.audio_rms.plugin_description"),
  //       icon: "mdi-waveform",
  //       plugin: "audio_rms",
  //       id: 101,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.audio_rms.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1000,
  //           max: 24000,
  //           value: 8000,
  //           step: 1000,
  //           name: "sr",
  //           text: t("modal.plugin.audio_waveform.sr"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.audio_frequency.plugin_name"),
  //       description: t("modal.plugin.audio_frequency.plugin_description"),
  //       icon: "mdi-waveform",
  //       plugin: "audio_freq",
  //       id: 102,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.audio_frequency.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1000,
  //           max: 24000,
  //           value: 8000,
  //           step: 1000,
  //           name: "sr",
  //           text: t("modal.plugin.audio_frequency.sr"),
  //         },
  //         {
  //           field: "slider",
  //           min: 64,
  //           max: 512,
  //           value: 256,
  //           step: 64, // TODO: only valid for values with power of 2
  //           name: "n_fft",
  //           text: t("modal.plugin.audio_frequency.n_fft"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.audio_waveform.plugin_name"),
  //       description: t("modal.plugin.audio_waveform.plugin_description"),
  //       icon: "mdi-waveform",
  //       plugin: "audio_amp",
  //       id: 103,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.audio_waveform.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1000,
  //           max: 24000,
  //           value: 8000,
  //           step: 1000,
  //           name: "sr",
  //           text: t("modal.plugin.audio_waveform.sr"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.whisper.plugin_name"),
  //       description: t("modal.plugin.whisper.plugin_description"),
  //       icon: "mdi-waveform",
  //       plugin: "whisper",
  //       id: 104,
  //       parameters: [],
  //       optional_parameters: [],
  //     },
  //   ],
  // },
  // {
  //   id: 2,
  //   name: t("modal.plugin.groups.face"),
  //   children: [
  //     {
  //       name: t("modal.plugin.face_clustering.plugin_name"),
  //       description: t("modal.plugin.face_clustering.plugin_description"),
  //       icon: "mdi-ungroup",
  //       plugin: "face_clustering",
  //       id: 201,
  //       parameters: [
  //         {
  //           field: "slider",
  //           min: 0.3,
  //           max: 0.7,
  //           value: 0.5,
  //           step: 0.01,
  //           name: "cluster_threshold",
  //           hint_right: t("modal.plugin.face_clustering.threshold.hint_right"),
  //           hint_left: t("modal.plugin.face_clustering.threshold.hint_left"),
  //         },
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 100,
  //           value: 50,
  //           step: 1,
  //           name: "max_cluster",
  //           hint_right: t("modal.plugin.face_clustering.max_cluster.hint_right"),
  //           hint_left: t("modal.plugin.face_clustering.max_cluster.hint_left"),
  //         },
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 100,
  //           value: 20,
  //           step: 1,
  //           name: "max_samples_per_cluster",
  //           hint_right: t("modal.plugin.face_clustering.max_faces.hint_right"),
  //           hint_left: t("modal.plugin.face_clustering.max_faces.hint_left"),
  //         },
  //         {
  //           field: "slider",
  //           min: 0,
  //           max: 1.0,
  //           value: 0.1,
  //           step: 0.05,
  //           name: "min_face_height",
  //           hint_right: t("modal.plugin.face_clustering.min_face_height.hint_right"),
  //           hint_left: t("modal.plugin.face_clustering.min_face_height.hint_left"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "select_options",
  //           text: t("modal.plugin.face_clustering.clustering_method_name"),
  //           items: ["Agglomerative", "DBScan"],
  //           name: "clustering_method",
  //           value: "DBScan",
  //         },
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.face_identification.plugin_name"),
  //       description: t("modal.plugin.face_identification.plugin_description"),
  //       icon: "mdi-account-search",
  //       plugin: "insightface_identification",
  //       id: 202,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.face_identification.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "image_input",
  //           file: null,
  //           name: "query_images",
  //           text: t("modal.plugin.face_identification.query_images"),
  //           hint: t("modal.plugin.face_identification.query_images_hint"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.faceemotion.plugin_name"),
  //       description: t("modal.plugin.faceemotion.plugin_description"),
  //       icon: "mdi-emoticon-happy-outline",
  //       plugin: "deepface_emotion",
  //       id: 203,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.faceemotion.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_timeline",
  //           name: "shot_timeline_id",
  //           // value: this.shot_timelines_names[0],
  //           // items: this.shot_timelines_names,
  //           text: t("modal.plugin.shot_timeline_name"),
  //           hint: t("modal.plugin.shot_timeline_hint"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //         {
  //           field: "slider",
  //           min: 24,
  //           max: 256,
  //           value: 48,
  //           step: 8,
  //           name: "min_facesize",
  //           text: t("modal.plugin.faceemotion.min_facesize"),
  //           disabled: true,
  //         },
  //       ],
  //     },
  //     // {
  //     //   name: t("modal.plugin.facesize.plugin_name"),
  //     //   icon: "mdi-face-recognition",
  //     //   plugin: "insightface_facesize",
  //     //   id: 204,
  //     //   parameters: [
  //     //     {
  //     //       field: "text_field",
  //     //       name: "timeline",
  //     //       value: t("modal.plugin.facesize.timeline_name"),
  //     //       text: t("modal.plugin.timeline_name"),
  //     //     },
  //     //     {
  //     //       field: "select_timeline",
  //     //       name: "shot_timeline_id",
  //     //       // value: this.shot_timelines_names[0],
  //     //       // items: this.shot_timelines_names,
  //     //       text: t("modal.plugin.shot_timeline_name"),
  //     //       hint: t("modal.plugin.shot_timeline_hint"),
  //     //     },
  //     //   ],
  //     //   optional_parameters: [
  //     //     {
  //     //       field: "slider",
  //     //       min: 1,
  //     //       max: 10,
  //     //       value: 2,
  //     //       step: 1,
  //     //       name: "fps",
  //     //       text: t("modal.plugin.fps"),
  //     //     },
  //     //   ],
  //     // },
  //   ],
  // },
  // {
  //   id: 3,
  //   name: t("modal.plugin.groups.color"),
  //   children: [
  //     {
  //       name: t("modal.plugin.color_analysis.plugin_name"),
  //       description: t("modal.plugin.color_analysis.plugin_description"),
  //       icon: "mdi-palette",
  //       plugin: "color_analysis",
  //       id: 301,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.color_analysis.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 8,
  //           value: 1,
  //           step: 1,
  //           name: "k",
  //           text: t("modal.plugin.color_analysis.slider"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //         {
  //           field: "slider",
  //           min: 24,
  //           max: 128,
  //           value: 48,
  //           step: 4,
  //           name: "max_resolution",
  //           text: t("modal.plugin.color_analysis.max_resolution"),
  //         },
  //         {
  //           field: "slider",
  //           min: 5,
  //           max: 25,
  //           value: 10,
  //           step: 5,
  //           name: "max_iter",
  //           text: t("modal.plugin.color_analysis.max_iter"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.color_brightness_analysis.plugin_name"),
  //       description: t("modal.plugin.color_brightness_analysis.plugin_description"),
  //       icon: "mdi-palette",
  //       plugin: "color_brightness_analysis",
  //       id: 302,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.color_brightness_analysis.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //         {
  //           field: "checkbox",
  //           name: "normalize",
  //           text: t("modal.plugin.normalize"),
  //           value: true,
  //         },
  //       ],
  //     },
  //   ],
  // },
  // {
  //   id: 4,
  //   name: t("modal.plugin.groups.identification"),
  //   children: [
  //     {
  //       name: t("modal.plugin.clip.plugin_name"),
  //       description: t("modal.plugin.clip.plugin_description"),
  //       icon: "mdi-eye",
  //       plugin: "clip",
  //       id: 403,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.clip.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "text_field",
  //           name: "search_term",
  //           value: "",
  //           text: t("modal.plugin.clip.search_term"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.clip_ontology.plugin_name"),
  //       description: t("modal.plugin.clip_ontology.plugin_description"),
  //       icon: "mdi-eye",
  //       plugin: "clip_ontology",
  //       id: 402,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.clip_ontology.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_timeline",
  //           name: "shot_timeline_id",
  //           // value: this.shot_timelines_names[0],
  //           // items: this.shot_timelines_names,
  //           text: t("modal.plugin.shot_timeline_name"),
  //           hint: t("modal.plugin.shot_timeline_hint"),
  //         },
  //         {
  //           field: "csv_input",
  //           file: null,
  //           name: "concept_csv",
  //           text: t("modal.plugin.clip_ontology.concepts"),
  //           hint: t("modal.plugin.clip_ontology.concepts_hint"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.x_clip.plugin_name"),
  //       description: t("modal.plugin.x_clip.plugin_description"),
  //       icon: "mdi-eye",
  //       plugin: "x_clip",
  //       id: 404,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.x_clip.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "text_field",
  //           name: "search_term",
  //           value: "",
  //           text: t("modal.plugin.x_clip.search_term"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.places_classification.plugin_name"),
  //       description: t("modal.plugin.places_classification.plugin_description"),
  //       icon: "mdi-map-marker",
  //       plugin: "places_classification",
  //       id: 401,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.places_classification.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_timeline",
  //           name: "shot_timeline_id",
  //           // value: this.shot_timelines_names[0],
  //           // items: this.shot_timelines_names,
  //           text: t("modal.plugin.shot_timeline_name"),
  //           hint: t("modal.plugin.shot_timeline_hint"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.place_clustering.plugin_name"),
  //       description: t("modal.plugin.place_clustering.plugin_description"),
  //       icon: "mdi-ungroup",
  //       plugin: "place_clustering",
  //       id: 405,
  //       parameters: [
  //         {
  //           field: "select_timeline",
  //           name: "shot_timeline_id",
  //           text: t("modal.plugin.shot_timeline_name"),
  //           hint: t("modal.plugin.shot_timeline_hint"),
  //         },
  //         //                {
  //         //                  field: "select_options",
  //         //                  text: t("modal.plugin.place_clustering.encoder_name"),
  //         //                  hint: t("modal.plugin.place_clustering.encoder_hint"),
  //         //                  items: ["CLIP", "Places"],
  //         //                  name: "encoder",
  //         //                },
  //         {
  //           field: "slider",
  //           min: 0.05,
  //           max: 0.3,
  //           value: 0.15,
  //           step: 0.01,
  //           name: "cluster_threshold",
  //           hint_right: t("modal.plugin.place_clustering.threshold.hint_right"),
  //           hint_left: t("modal.plugin.place_clustering.threshold.hint_left"),
  //         },
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 100,
  //           value: 50,
  //           step: 1,
  //           name: "max_cluster",
  //           hint_right: t("modal.plugin.place_clustering.max_cluster.hint_right"),
  //           hint_left: t("modal.plugin.place_clustering.max_cluster.hint_left"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "select_options",
  //           text: t("modal.plugin.place_clustering.clustering_method_name"),
  //           items: ["Agglomerative", "DBScan"],
  //           name: "clustering_method",
  //           value: "DBScan",
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.blip.plugin_name"),
  //       description: t("modal.plugin.blip.plugin_description"),
  //       icon: "mdi-eye",
  //       plugin: "blip_vqa",
  //       id: 406,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.blip.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_timeline",
  //           name: "shot_timeline_id",
  //           // value: this.shot_timelines_names[0],
  //           // items: this.shot_timelines_names,
  //           text: t("modal.plugin.shot_timeline_name"),
  //           hint: t("modal.plugin.shot_timeline_hint"),
  //         },
  //         {
  //           field: "text_field",
  //           name: "query_term",
  //           value: "",
  //           text: t("modal.plugin.blip.search_term"),
  //         },
  //       ],
  //       optional_parameters: [],
  //     },
  //     {
  //       name: t("modal.plugin.ocr.plugin_name"),
  //       icon: "mdi-text-shadow",
  //       plugin: "ocr_video_detector_onnx",
  //       id: 407,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.ocr.timeline_name"),
  //           text: t("modal.plugin.ocr.timeline_name"),
  //         },
  //         {
  //           field: "text_field",
  //           name: "search_term",
  //           value: "",
  //           text: t("modal.plugin.ocr.search_term"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //   ],
  // },
  // {
  //   id: 5,
  //   name: t("modal.plugin.groups.shot"),
  //   children: [
  //     {
  //       name: t("modal.plugin.shot_detection.plugin_name"),
  //       description: t("modal.plugin.shot_detection.plugin_description"),
  //       icon: "mdi-arrow-expand-horizontal",
  //       plugin: "shotdetection",
  //       id: 501,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.shot_detection.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.shot_density.plugin_name"),
  //       description: t("modal.plugin.shot_density.plugin_description"),
  //       icon: "mdi-sine-wave",
  //       plugin: "shot_density",
  //       id: 503,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.shot_density.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_timeline",
  //           name: "shot_timeline_id",
  //           text: t("modal.plugin.shot_density.input_timeline"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 60,
  //           value: 10,
  //           step: 1,
  //           name: "bandwidth",
  //           text: t("modal.plugin.shot_density.bandwidth"),
  //         },
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 10,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.shot_type_classification.plugin_name"),
  //       description: t("modal.plugin.shot_type_classification.plugin_description"),
  //       icon: "mdi-video-switch",
  //       plugin: "shot_type_classification",
  //       id: 504,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.shot_type_classification.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_timeline",
  //           name: "shot_timeline_id",
  //           text: t("modal.plugin.shot_timeline_name"),
  //           hint: t("modal.plugin.shot_timeline_hint"),
  //         },
  //       ],
  //       optional_parameters: [
  //         {
  //           field: "slider",
  //           min: 1,
  //           max: 10,
  //           value: 2,
  //           step: 1,
  //           name: "fps",
  //           text: t("modal.plugin.fps"),
  //         },
  //       ],
  //     },
  //     {
  //       name: t("modal.plugin.shot_scalar_annotation.plugin_name"),
  //       description: t("modal.plugin.shot_scalar_annotation.plugin_description"),
  //       icon: "mdi-label-outline",
  //       plugin: "shot_scalar_annotation",
  //       id: 505,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.shot_scalar_annotation.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_timeline",
  //           name: "shot_timeline_id",
  //           text: t("modal.plugin.shot_timeline_name"),
  //           hint: t("modal.plugin.shot_timeline_hint"),
  //         },
  //         {
  //           field: "select_scalar_timeline",
  //           name: "scalar_timeline_id",
  //           text: t("modal.plugin.scalar_timeline_name"),
  //           hint: t("modal.plugin.scalar_timeline_hint"),
  //         },
  //       ],
  //       optional_parameters: [],
  //     },
  //     {
  //       name: t("modal.plugin.thumbnail.plugin_name"),
  //       description: t("modal.plugin.thumbnail.plugin_description"),
  //       icon: "mdi-image-multiple",
  //       plugin: "thumbnail",
  //       id: 502,
  //       parameters: [],
  //       optional_parameters: [],
  //     },
  //   ],
  // },
  // {
  //   id: 6,
  //   name: t("modal.plugin.groups.aggregation"),
  //   children: [
  //     {
  //       name: t("modal.plugin.aggregation.plugin_name"),
  //       description: t("modal.plugin.aggregation.plugin_description"),
  //       icon: "mdi-sigma",
  //       plugin: "aggregate_scalar",
  //       id: 601,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.aggregation.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_scalar_timelines",
  //           name: "timeline_ids",
  //           text: t("modal.plugin.scalar_timeline_name"),
  //           hint: t("modal.plugin.scalar_timeline_hint"),
  //         },
  //         {
  //           field: "buttongroup",
  //           text: t("modal.plugin.aggregation.method"),
  //           name: "aggregation",
  //           value: 0,
  //           buttons: [
  //             t("modal.plugin.aggregation.logical_or"),
  //             t("modal.plugin.aggregation.logical_and"),
  //             t("modal.plugin.aggregation.mean"),
  //             t("modal.plugin.aggregation.prod"),
  //           ],
  //         },
  //       ],
  //       optional_parameters: [],
  //     },
  //     {
  //       name: t("modal.plugin.invert.plugin_name"),
  //       description: t("modal.plugin.invert.plugin_description"),
  //       icon: "mdi-numeric-negative-1",
  //       plugin: "invert_scalar",
  //       id: 602,
  //       parameters: [
  //         {
  //           field: "text_field",
  //           name: "timeline",
  //           value: t("modal.plugin.invert.timeline_name"),
  //           text: t("modal.plugin.timeline_name"),
  //         },
  //         {
  //           field: "select_scalar_timeline",
  //           name: "scalar_timeline_id",
  //           text: t("modal.plugin.scalar_timeline_name"),
  //           hint: t("modal.plugin.scalar_timeline_hint"),
  //         },
  //       ],
  //       optional_parameters: [],
  //     },
  //   ],
  // },
  {
    id: 7,
    name: t("modal.plugin.groups.tracking"),
    children: [
      {
        name: t("modal.plugin.bytetrack.plugin_name"),
        description: t("modal.plugin.bytetrack.plugin_description"),
        icon: "mdi-account-box-outline",
        plugin: "bytetrack",
        id: 701,
        parameters: [
          {
            field: "slider",
            min: 1,
            max: 30,
            value: Math.round(playerStore.videoFPS),
            step: 1,
            name: "fps",
            text: t("modal.plugin.fps"),
            dataTour: "bytetrack-fps",
          },
        ],
        optional_parameters: [],
      },
      {
        name: t("modal.plugin.object_tracker.plugin_name"),
        description: t("modal.plugin.object_tracker.plugin_description"),
        icon: "mdi-radar",
        plugin: "object_tracker",
        id: 704,
        parameters: [
          {
            field: "slider",
            min: 1,
            max: 30,
            value: Math.round(playerStore.videoFPS),
            step: 1,
            name: "fps",
            text: t("modal.plugin.fps"),
          },
          {
            field: "select_options",
            name: "tracking_target",
            value: "player",
            items: [
              {
                title: t("modal.plugin.object_tracker.tracking_target_player"),
                value: "player",
              },
              { title: t("modal.plugin.object_tracker.tracking_target_ball"), value: "ball" },
            ],
            text: t("modal.plugin.object_tracker.tracking_target"),
          },
          {
            field: "select_options",
            name: "detector",
            value: "yolox",
            items: ALL_OBJECT_TRACKER_DETECTOR_ITEMS,
            text: t("modal.plugin.object_tracker.detector"),
          },
          {
            field: "select_options",
            name: "tracker",
            value: "bytetrack",
            items: [{ title: "ByteTrack", value: "bytetrack" }],
            text: t("modal.plugin.object_tracker.tracker"),
          },
        ],
        optional_parameters: [
          {
            field: "slider",
            min: 0,
            max: 1,
            value: 0.2,
            step: 0.05,
            name: "confidence_threshold",
            text: t("modal.plugin.object_tracker.confidence_threshold"),
            group: "detector_params",
          },
          {
            field: "slider",
            min: 1,
            max: 16,
            value: 1,
            step: 1,
            name: "batch_size",
            text: t("modal.plugin.object_tracker.batch_size"),
            group: "detector_params",
          },
          {
            field: "slider",
            min: 0,
            max: 1,
            value: 0.65,
            step: 0.05,
            name: "nms_thresh",
            text: t("modal.plugin.object_tracker.nms_thresh"),
            group: "detector_params",
          },
          {
            field: "slider",
            min: 0,
            max: 1,
            value: 0.3,
            step: 0.05,
            name: "iou",
            text: t("modal.plugin.object_tracker.iou"),
            group: "detector_params",
            hidden: true,
          },
          {
            field: "checkbox",
            value: false,
            name: "agnostic_nms",
            text: t("modal.plugin.object_tracker.agnostic_nms"),
            group: "detector_params",
            hidden: true,
          },
          {
            field: "checkbox",
            value: true,
            name: "fp16",
            text: t("modal.plugin.object_tracker.fp16"),
            group: "detector_params",
          },
          {
            field: "checkbox",
            value: false,
            name: "half",
            text: t("modal.plugin.object_tracker.half"),
            group: "detector_params",
            hidden: true,
          },
          {
            field: "checkbox",
            value: true,
            name: "decode",
            text: t("modal.plugin.object_tracker.decode"),
            group: "detector_params",
          },
          {
            field: "slider",
            min: 1,
            max: 10,
            value: 1,
            step: 1,
            name: "num_classes",
            text: t("modal.plugin.object_tracker.num_classes"),
            group: "detector_params",
          },
          {
            field: "slider",
            min: 1,
            max: 300,
            value: 100,
            step: 1,
            name: "max_det",
            text: t("modal.plugin.object_tracker.max_det"),
            group: "detector_params",
            hidden: true,
          },
          {
            field: "slider",
            min: 56,
            max: 1400,
            value: 1288,
            step: 56,
            name: "resolution",
            text: t("modal.plugin.object_tracker.resolution"),
            group: "detector_params",
            hidden: true,
          },
          {
            field: "checkbox",
            value: false,
            name: "verbose",
            text: t("modal.plugin.object_tracker.verbose"),
            group: "detector_params",
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 1,
            value: 0.4,
            step: 0.05,
            name: "track_thresh",
            text: t("modal.plugin.object_tracker.track_thresh"),
            group: "tracker_params",
          },
          {
            field: "slider",
            min: 1,
            max: 600,
            value: 300,
            step: 10,
            name: "track_buffer",
            text: t("modal.plugin.object_tracker.track_buffer"),
            group: "tracker_params",
          },
          {
            field: "slider",
            min: 0,
            max: 1,
            value: 0.8,
            step: 0.05,
            name: "match_thresh",
            text: t("modal.plugin.object_tracker.match_thresh"),
            group: "tracker_params",
          },
          {
            field: "checkbox",
            value: false,
            name: "mot20",
            text: t("modal.plugin.object_tracker.mot20"),
            group: "tracker_params",
          },
          {
            field: "slider",
            min: 0,
            max: 10,
            value: 5.0,
            step: 0.1,
            name: "aspect_ratio_thresh",
            text: t("modal.plugin.object_tracker.aspect_ratio_thresh"),
            group: "tracker_params",
          },
          {
            field: "slider",
            min: 0,
            max: 500,
            value: 0,
            step: 10,
            name: "min_box_area",
            text: t("modal.plugin.object_tracker.min_box_area"),
            group: "tracker_params",
          },
        ],
      },
      {
        name: t("modal.plugin.team_clustering.plugin_name"),
        description: t("modal.plugin.team_clustering.plugin_description"),
        icon: "mdi-account-group",
        plugin: "team_clustering",
        id: 705,
        parameters: [
          {
            field: "select_object_tracker_run",
            name: "object_tracker_id",
            value: "",
            text: t("modal.plugin.team_clustering.object_tracker_id"),
            hint: t("modal.plugin.team_clustering.object_tracker_id_hint"),
            no_data_text: "modal.plugin.team_clustering.object_tracker_run_none",
          },
          {
            field: "select_options",
            name: "clustering_algo",
            value: "KMEANS",
            items: [
              { title: "K-Means", value: "KMEANS" },
              { title: "HDBSCAN", value: "HDBSCAN" },
            ],
            text: t("modal.plugin.team_clustering.clustering_algo"),
          },
          {
            field: "slider",
            min: 2,
            max: 16,
            value: 2,
            step: 1,
            name: "K",
            text: t("modal.plugin.team_clustering.K"),
          },
        ],
        optional_parameters: [
          {
            field: "slider",
            min: 1,
            max: 50,
            value: 2,
            step: 1,
            name: "min_samples_per_track",
            text: t("modal.plugin.team_clustering.min_samples_per_track"),
          },
          {
            field: "slider",
            min: 5,
            max: 100,
            value: 20,
            step: 1,
            name: "max_samples_per_track",
            text: t("modal.plugin.team_clustering.max_samples_per_track"),
          },
          {
            field: "slider",
            min: 1,
            max: 100,
            value: 3,
            step: 1,
            name: "min_cluster_size",
            text: t("modal.plugin.team_clustering.min_cluster_size"),
          },
          {
            field: "slider",
            min: 12,
            max: 500,
            value: 12,
            step: 4,
            name: "min_pixels",
            text: t("modal.plugin.team_clustering.min_pixels"),
          },
          {
            field: "checkbox",
            value: false,
            name: "use_illumination_norm",
            text: t("modal.plugin.team_clustering.use_illumination_norm"),
          },
          {
            field: "checkbox",
            value: false,
            name: "use_central_band",
            text: t("modal.plugin.team_clustering.use_central_band"),
          },
          {
            field: "checkbox",
            value: false,
            name: "use_torso_crop",
            text: t("modal.plugin.team_clustering.use_torso_crop"),
          },
          {
            field: "checkbox",
            value: false,
            name: "use_green_mask",
            text: t("modal.plugin.team_clustering.use_green_mask"),
          },
          {
            field: "checkbox",
            value: false,
            name: "use_gray_mask",
            text: t("modal.plugin.team_clustering.use_gray_mask"),
          },
          {
            field: "checkbox",
            value: true,
            name: "two_channel",
            text: t("modal.plugin.team_clustering.two_channel"),
          },
          {
            field: "checkbox",
            value: true,
            name: "use_pca",
            text: t("modal.plugin.team_clustering.use_pca"),
          },
          {
            field: "slider",
            min: 2,
            max: 128,
            value: 16,
            step: 1,
            name: "pca_components",
            text: t("modal.plugin.team_clustering.pca_components"),
            hidden: true,
          },
          {
            field: "select_options",
            name: "metric",
            value: "euclidean",
            items: [
              { title: "Euclidean", value: "euclidean" },
              { title: "Cosine", value: "cosine" },
            ],
            text: t("modal.plugin.team_clustering.metric"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0.01,
            max: 0.99,
            value: 0.5,
            step: 0.01,
            name: "cluster_selection_epsilon",
            text: t("modal.plugin.team_clustering.cluster_selection_epsilon"),
            hidden: true,
          },
          {
            field: "slider",
            min: 1,
            max: 100,
            value: 20,
            step: 1,
            name: "n_init",
            text: t("modal.plugin.team_clustering.n_init"),
            hidden: false,
          },
          {
            field: "slider",
            min: 0,
            max: 9999,
            value: 42,
            step: 1,
            name: "random_state",
            text: t("modal.plugin.team_clustering.random_state"),
            hidden: false,
          },
          {
            field: "slider",
            min: 4,
            max: 64,
            value: 16,
            step: 1,
            name: "hist_h_bins",
            text: t("modal.plugin.team_clustering.hist_h_bins"),
            hidden: true,
          },
          {
            field: "slider",
            min: 1,
            max: 32,
            value: 4,
            step: 1,
            name: "hist_s_bins",
            text: t("modal.plugin.team_clustering.hist_s_bins"),
            hidden: true,
          },
          {
            field: "slider",
            min: 1,
            max: 32,
            value: 4,
            step: 1,
            name: "hist_v_bins",
            text: t("modal.plugin.team_clustering.hist_v_bins"),
            hidden: true,
          },
          {
            field: "slider",
            min: 6,
            max: 200,
            value: 12,
            step: 1,
            name: "min_crop_w",
            text: t("modal.plugin.team_clustering.min_crop_w"),
            hidden: true,
          },
          {
            field: "slider",
            min: 12,
            max: 400,
            value: 24,
            step: 1,
            name: "min_crop_h",
            text: t("modal.plugin.team_clustering.min_crop_h"),
            hidden: true,
          },
          {
            field: "slider",
            min: 5,
            max: 512,
            value: 128,
            step: 1,
            name: "crop_size_x",
            text: t("modal.plugin.team_clustering.crop_size_x"),
            hidden: true,
          },
          {
            field: "slider",
            min: 5,
            max: 512,
            value: 256,
            step: 1,
            name: "crop_size_y",
            text: t("modal.plugin.team_clustering.crop_size_y"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 0.8,
            value: 0,
            step: 0.05,
            name: "crop_x1_offset",
            text: t("modal.plugin.team_clustering.crop_x1_offset"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 0.8,
            value: 0,
            step: 0.05,
            name: "crop_y1_offset",
            text: t("modal.plugin.team_clustering.crop_y1_offset"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 0.8,
            value: 0,
            step: 0.05,
            name: "crop_x2_offset",
            text: t("modal.plugin.team_clustering.crop_x2_offset"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 0.8,
            value: 0,
            step: 0.05,
            name: "crop_y2_offset",
            text: t("modal.plugin.team_clustering.crop_y2_offset"),
            hidden: true,
          },
        ],
      },
      {
        name: t("modal.plugin.osnet_reid.plugin_name"),
        description: t("modal.plugin.osnet_reid.plugin_description"),
        icon: "mdi-account-search",
        plugin: "osnet_reid",
        id: 706,
        parameters: [
          {
            field: "select_object_tracker_run",
            name: "object_tracker_id",
            value: "",
            text: t("modal.plugin.osnet_reid.object_tracker_id"),
            hint: t("modal.plugin.osnet_reid.object_tracker_id_hint"),
            no_data_text: "modal.plugin.team_clustering.object_tracker_run_none",
          },
          {
            field: "select_options",
            name: "gallery_mode",
            value: "protos",
            items: [
              { title: t("modal.plugin.osnet_reid.gallery_mode_protos"), value: "protos" },
              { title: t("modal.plugin.osnet_reid.gallery_mode_tracks"), value: "tracks" },
            ],
            text: t("modal.plugin.osnet_reid.gallery_mode"),
          },
          {
            field: "select_options",
            name: "model_name",
            value: "osnet_x1_0",
            items: [
              { title: "OSNet x1.0", value: "osnet_x1_0" },
              { title: "OSNet-IBN x1.0", value: "osnet_ibn_x1_0" },
              { title: "OSNet-AIN x1.0", value: "osnet_ain_x1_0" },
            ],
            text: t("modal.plugin.osnet_reid.model_name"),
          },
        ],
        optional_parameters: [
          {
            field: "text_field",
            name: "checkpoint",
            value: "/models/reid/osnet_x1_0_ms_d_c.pth.tar",
            hidden: true,
          },
          {
            field: "slider",
            min: 0.6,
            max: 0.9,
            value: 0.72,
            step: 0.01,
            name: "match_thresh",
            text: t("modal.plugin.osnet_reid.match_thresh"),
          },
          {
            field: "slider",
            min: 0.85,
            max: 0.95,
            value: 0.85,
            step: 0.01,
            name: "update_threshold",
            text: t("modal.plugin.osnet_reid.update_threshold"),
          },
          {
            field: "slider",
            min: 0.98,
            max: 0.99,
            value: 0.98,
            step: 0.001,
            name: "ema_alpha",
            text: t("modal.plugin.osnet_reid.ema_alpha"),
          },
          {
            field: "slider",
            min: 0.05,
            max: 0.08,
            value: 0.06,
            step: 0.005,
            name: "margin",
            text: t("modal.plugin.osnet_reid.margin"),
          },
          {
            field: "slider",
            min: 0.65,
            max: 0.8,
            value: 0.7,
            step: 0.01,
            name: "prototype_weight",
            text: t("modal.plugin.osnet_reid.prototype_weight"),
          },
          {
            field: "slider",
            min: 0.2,
            max: 0.35,
            value: 0.3,
            step: 0.01,
            name: "cache_weight",
            text: t("modal.plugin.osnet_reid.cache_weight"),
          },
          {
            field: "slider",
            min: 8,
            max: 12,
            value: 10,
            step: 1,
            name: "cache_size",
            text: t("modal.plugin.osnet_reid.cache_size"),
          },
          {
            field: "slider",
            min: 90,
            max: 300,
            value: 120,
            step: 10,
            name: "max_missed",
            text: t("modal.plugin.osnet_reid.max_missed"),
          },
          {
            field: "slider",
            min: 5,
            max: 512,
            value: 128,
            step: 1,
            name: "crop_size_x",
            text: t("modal.plugin.osnet_reid.crop_size_x"),
            hidden: true,
          },
          {
            field: "slider",
            min: 5,
            max: 512,
            value: 256,
            step: 1,
            name: "crop_size_y",
            text: t("modal.plugin.osnet_reid.crop_size_y"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 0.8,
            value: 0,
            step: 0.05,
            name: "crop_x1_offset",
            text: t("modal.plugin.osnet_reid.crop_x1_offset"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 0.8,
            value: 0,
            step: 0.05,
            name: "crop_y1_offset",
            text: t("modal.plugin.osnet_reid.crop_y1_offset"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 0.8,
            value: 0,
            step: 0.05,
            name: "crop_x2_offset",
            text: t("modal.plugin.osnet_reid.crop_x2_offset"),
            hidden: true,
          },
          {
            field: "slider",
            min: 0,
            max: 0.8,
            value: 0,
            step: 0.05,
            name: "crop_y2_offset",
            text: t("modal.plugin.osnet_reid.crop_y2_offset"),
            hidden: true,
          },
        ],
      },
      {
        name: t("modal.plugin.calibration_static_dlt.plugin_name"),
        description: t("modal.plugin.calibration_static_dlt.plugin_description"),
        icon: "mdi-camera-enhance",
        plugin: "calibration_static_dlt",
        id: 702,
        parameters: [
          {
            field: "select_calibration",
            // field: "text_field",
            name: "calibration_id",
            value: "",
            text: t("modal.plugin.calibration_static_dlt.calibration_id"),
            hint: t("modal.plugin.calibration_static_dlt.calibration_id_hint"),
          },
        ],
        optional_parameters: [],
      },
      {
        name: t("modal.plugin.kpi_computation.plugin_name"),
        description: t("modal.plugin.kpi_computation.plugin_description"),
        icon: "mdi-chart-line",
        plugin: "kpi_computation",
        id: 703,
        parameters: [
          {
            field: "select_options",
            name: "format",
            value: "kinexon",
            items: [
              ...positionDataStore.provider.map((p) => ({ title: p.name, value: p.id })),
              { title: "SportVid (ByteTrack)", value: "sportvid" },
            ],
            text: t("modal.plugin.kpi_computation.format"),
            dataTour: "kpi-format",
          },
          {
            field: "select_tracking_data",
            name: "tracking_data_id",
            value: "",
            text: t("modal.plugin.kpi_computation.tracking_data_id"),
            hint: t("modal.plugin.kpi_computation.tracking_data_id_hint"),
            format_filter: "kinexon",
            dataTour: "kpi-tracking-data",
          },
          {
            field: "select_bytetrack_run",
            name: "bytetrack_run_id",
            value: "",
            text: t("modal.plugin.kpi_computation.bytetrack_run_id"),
            hint: t("modal.plugin.kpi_computation.bytetrack_run_id_hint"),
            hidden: true,
            dataTour: "kpi-bytetrack-run",
          },
          {
            field: "select_calibration",
            name: "calibration_id",
            value: "",
            text: t("modal.plugin.kpi_computation.calibration_id"),
            hint: t("modal.plugin.kpi_computation.calibration_id_hint"),
            hidden: true,
            dlt: true,
            dataTour: "kpi-calibration",
          },
        ],
        optional_parameters: [
          {
            field: "select_options",
            name: "filter_type",
            value: "",
            items: [
              { title: t("modal.plugin.kpi_computation.filter_none"), value: "" },
              {
                title: t("modal.plugin.kpi_computation.filter_butterworth"),
                value: "butterworth_lowpass",
              },
              { title: t("modal.plugin.kpi_computation.filter_savgol"), value: "savgol_lowpass" },
            ],
            text: t("modal.plugin.kpi_computation.filter_type"),
            dataTour: "kpi-filter-type",
          },
          {
            field: "slider",
            name: "order",
            value: 3,
            min: 1,
            max: 10,
            step: 1,
            text: t("modal.plugin.kpi_computation.order"),
            hidden: true,
          },
          {
            field: "slider",
            name: "Wn",
            value: 1.0,
            min: 0.01,
            max: 10.0,
            step: 0.01,
            text: t("modal.plugin.kpi_computation.Wn"),
            hidden: true,
          },
          {
            field: "slider",
            name: "window_length",
            value: 5,
            min: 3,
            max: 51,
            step: 2,
            text: t("modal.plugin.kpi_computation.window_length"),
            hidden: true,
          },
          {
            field: "slider",
            name: "poly_order",
            value: 3,
            min: 1,
            max: 10,
            step: 1,
            text: t("modal.plugin.kpi_computation.poly_order"),
            hidden: true,
          },
        ],
      },
    ],
  },
  // TODO: add extra view for all calibration plugins
]);

// Toggle visibility of filter hyperparameters for kpi_computation based on selected filter_type
const kpiOptionalParams = computed(() => {
  const group = plugins.value.find((g) => g.id === 7);
  const plugin = group?.children.find((p) => p.id === 703);
  return plugin?.optional_parameters || [];
});

watch(
  () => kpiOptionalParams.value.find((p) => p.name === "filter_type")?.value,
  (filterType) => {
    for (const p of kpiOptionalParams.value) {
      if (p.name === "order" || p.name === "Wn") {
        p.hidden = filterType !== "butterworth_lowpass";
      } else if (p.name === "window_length" || p.name === "poly_order") {
        p.hidden = filterType !== "savgol_lowpass";
      }
    }
  },
  { immediate: true }
);

// Toggle tracking_data_id / bytetrack_run_id visibility based on format
const kpiParams = computed(() => {
  const group = plugins.value.find((g) => g.id === 7);
  const plugin = group?.children.find((p) => p.id === 703);
  return plugin?.parameters || [];
});

watch(
  () => kpiParams.value.find((p) => p.name === "format")?.value,
  (fmt) => {
    const trackingParam = kpiParams.value.find((p) => p.name === "tracking_data_id");
    const bytetrackParam = kpiParams.value.find((p) => p.name === "bytetrack_run_id");
    const calibrationParam = kpiParams.value.find((p) => p.name === "calibration_id");
    if (trackingParam) {
      trackingParam.hidden = fmt === "sportvid";
      trackingParam.format_filter = fmt !== "sportvid" ? fmt : null;
      trackingParam.value = "";
    }
    if (bytetrackParam) bytetrackParam.hidden = fmt !== "sportvid";
    if (calibrationParam) calibrationParam.hidden = fmt !== "sportvid";
  },
  { immediate: true }
);

// Toggle visibility of detector-specific parameters for object_tracker based on selected detector
const DETECTOR_PARAM_VISIBILITY = {
  yolox: ["confidence_threshold", "batch_size", "nms_thresh", "fp16", "decode", "num_classes"],
  yolo10: [
    "confidence_threshold",
    "batch_size",
    "iou",
    "agnostic_nms",
    "half",
    "max_det",
    "verbose",
  ],
  yolo11: [
    "confidence_threshold",
    "batch_size",
    "iou",
    "agnostic_nms",
    "half",
    "max_det",
    "verbose",
  ],
  yolo12: [
    "confidence_threshold",
    "batch_size",
    "iou",
    "agnostic_nms",
    "half",
    "max_det",
    "verbose",
  ],
  yolo26: [
    "confidence_threshold",
    "batch_size",
    "iou",
    "agnostic_nms",
    "half",
    "max_det",
    "verbose",
  ],
  rfdetr: ["confidence_threshold", "batch_size", "max_det", "resolution", "verbose"],
  rtdetr: ["confidence_threshold", "batch_size", "verbose"],
};

const DETECTOR_CONFIDENCE_DEFAULT = {
  yolox: 0.2,
  yolo10: 0.2,
  yolo11: 0.2,
  yolo12: 0.2,
  yolo26: 0.2,
  rfdetr: 0.5,
  rtdetr: 0.25,
};

const objectTrackerParams = computed(() => {
  const group = plugins.value.find((g) => g.id === 7);
  const plugin = group?.children.find((p) => p.id === 704);
  return plugin?.parameters || [];
});

const objectTrackerOptionalParams = computed(() => {
  const group = plugins.value.find((g) => g.id === 7);
  const plugin = group?.children.find((p) => p.id === 704);
  return plugin?.optional_parameters || [];
});

watch(
  () => objectTrackerParams.value.find((p) => p.name === "detector")?.value,
  (detector) => {
    const visible = DETECTOR_PARAM_VISIBILITY[detector] || [];
    for (const p of objectTrackerOptionalParams.value) {
      if (p.group !== "detector_params") continue;
      p.hidden = !visible.includes(p.name);
    }
    const confidenceParam = objectTrackerOptionalParams.value.find(
      (p) => p.name === "confidence_threshold"
    );
    if (confidenceParam && detector in DETECTOR_CONFIDENCE_DEFAULT) {
      confidenceParam.value = DETECTOR_CONFIDENCE_DEFAULT[detector];
    }
  },
  { immediate: true }
);

// Toggle between "player" and "ball" tracking runs of object_tracker: restricts the detector
// choices, hides the tracker (ByteTrack) and all tracker_params fields for ball runs (no
// tracker for ball detections), and adjusts detector confidence/iou defaults accordingly.
const BALL_TARGET_DETECTORS = ["yolo11", "yolo12", "rfdetr"];
const BALL_RFDETR_CONFIDENCE_DEFAULT = 0.2;
const BALL_YOLO_IOU_DEFAULT = 0.5;
const PLAYER_IOU_DEFAULT = 0.3;

watch(
  () => [
    objectTrackerParams.value.find((p) => p.name === "tracking_target")?.value,
    objectTrackerParams.value.find((p) => p.name === "detector")?.value,
  ],
  ([target, detector]) => {
    const detectorParam = objectTrackerParams.value.find((p) => p.name === "detector");
    const trackerParam = objectTrackerParams.value.find((p) => p.name === "tracker");
    const trackerParamFields = objectTrackerOptionalParams.value.filter(
      (p) => p.group === "tracker_params"
    );
    const confidenceParam = objectTrackerOptionalParams.value.find(
      (p) => p.name === "confidence_threshold"
    );
    const iouParam = objectTrackerOptionalParams.value.find((p) => p.name === "iou");

    if (target === "ball") {
      detectorParam.items = BALL_OBJECT_TRACKER_DETECTOR_ITEMS;
      if (!BALL_TARGET_DETECTORS.includes(detector)) {
        detectorParam.value = "yolo11";
        return;
      }
      if (trackerParam) trackerParam.hidden = true;
      for (const p of trackerParamFields) p.hidden = true;

      if (detector === "rfdetr" && confidenceParam) {
        confidenceParam.value = BALL_RFDETR_CONFIDENCE_DEFAULT;
      }
      if ((detector === "yolo11" || detector === "yolo12") && iouParam) {
        iouParam.value = BALL_YOLO_IOU_DEFAULT;
      }
    } else {
      detectorParam.items = ALL_OBJECT_TRACKER_DETECTOR_ITEMS;
      if (trackerParam) trackerParam.hidden = false;
      for (const p of trackerParamFields) p.hidden = false;

      if (iouParam) iouParam.value = PLAYER_IOU_DEFAULT;
      if (confidenceParam && detector in DETECTOR_CONFIDENCE_DEFAULT) {
        confidenceParam.value = DETECTOR_CONFIDENCE_DEFAULT[detector];
      }
    }
  },
  { immediate: true }
);

const teamClusteringParams = computed(() => {
  const group = plugins.value.find((g) => g.id === 7);
  const plugin = group?.children.find((p) => p.id === 705);
  return plugin?.parameters || [];
});

const teamClusteringOptionalParams = computed(() => {
  const group = plugins.value.find((g) => g.id === 7);
  const plugin = group?.children.find((p) => p.id === 705);
  return plugin?.optional_parameters || [];
});

// Only relevant for HDBSCAN: distance metric and cluster-selection epsilon.
const HDBSCAN_ONLY_PARAMS = ["metric", "cluster_selection_epsilon"];
// Only relevant for K-Means: number of initializations and the random seed.
const KMEANS_ONLY_PARAMS = ["n_init", "random_state"];

watch(
  () => teamClusteringParams.value.find((p) => p.name === "clustering_algo")?.value,
  (algo) => {
    for (const p of teamClusteringOptionalParams.value) {
      if (HDBSCAN_ONLY_PARAMS.includes(p.name)) p.hidden = algo !== "HDBSCAN";
      if (KMEANS_ONLY_PARAMS.includes(p.name)) p.hidden = algo !== "KMEANS";
    }
  },
  { immediate: true }
);

watch(
  () => teamClusteringOptionalParams.value.find((p) => p.name === "use_pca")?.value,
  (usePca) => {
    const pcaComponentsParam = teamClusteringOptionalParams.value.find(
      (p) => p.name === "pca_components"
    );
    if (pcaComponentsParam) pcaComponentsParam.hidden = !usePca;
  },
  { immediate: true }
);

const osnetReidParams = computed(() => {
  const group = plugins.value.find((g) => g.id === 7);
  const plugin = group?.children.find((p) => p.id === 706);
  return plugin?.parameters || [];
});

const osnetReidOptionalParams = computed(() => {
  const group = plugins.value.find((g) => g.id === 7);
  const plugin = group?.children.find((p) => p.id === 706);
  return plugin?.optional_parameters || [];
});

// Only relevant for gallery_mode "protos" (ProtoGallery): prototype/cache-based matching
// hyperparameters. "tracks" mode (Gallery) only uses match_thresh & max_missed.
const PROTOS_ONLY_PARAMS = [
  "update_threshold",
  "ema_alpha",
  "cache_size",
  "margin",
  "prototype_weight",
  "cache_weight",
];

watch(
  () => osnetReidParams.value.find((p) => p.name === "gallery_mode")?.value,
  (galleryMode) => {
    for (const p of osnetReidOptionalParams.value) {
      if (PROTOS_ONLY_PARAMS.includes(p.name)) p.hidden = galleryMode !== "protos";
    }
  },
  { immediate: true }
);

const MODEL_CHECKPOINT_MAP = {
  osnet_x1_0: "/models/reid/osnet_x1_0_ms_d_c.pth.tar",
  osnet_ain_x1_0: "/models/reid/osnet_ain_ms_d_c.pt.tarh",
  osnet_ibn_x1_0: "/models/reid/osnet_ibn_ms_d_c.pth.tar",
};

watch(
  () => osnetReidParams.value.find((p) => p.name === "model_name")?.value,
  (modelName) => {
    const checkpointParam = osnetReidOptionalParams.value.find((p) => p.name === "checkpoint");
    if (checkpointParam && modelName in MODEL_CHECKPOINT_MAP) {
      checkpointParam.value = MODEL_CHECKPOINT_MAP[modelName];
    }
  },
  { immediate: true }
);

const pluginsSorted = computed(() => {
  return plugins.value.slice(0).sort((a, b) => a.name.localeCompare(b.name));
});

const selected = computed(() => {
  if (!activeNode.value.length) return undefined;

  const id = activeNode.value[0];
  if (id < 100) return undefined;

  let plugin_group = plugins.value.find((group) => group.id === parseInt(id / 100));
  let plugin = plugin_group?.children.find((plugin) => plugin.id === id);

  return plugin;
});

// Ball vs. player class filters per detector, keyed by tracking_target. The frontend has no
// UI control for `classes` -- it's derived here from the (UI-only) tracking_target parameter,
// which is stripped from the payload afterwards since the backend doesn't know that field.
const OBJECT_TRACKER_CLASSES_BY_TARGET = {
  ball: {
    yolo11: [32],
    yolo12: [32],
    rfdetr: ["ball"],
  },
  player: {
    yolox: [0],
    yolo10: [0],
    yolo11: [0],
    yolo12: [0],
    yolo26: [0],
    rtdetr: [0],
    rfdetr: ["player", "referee", "goalkeeper"],
  },
};

const runPlugin = async (plugin, parameters, optional_parameters) => {
  parameters = [...parameters, ...optional_parameters];

  if (plugin === "object_tracker") {
    const trackingTargetIndex = parameters.findIndex((e) => e.name === "tracking_target");
    if (trackingTargetIndex >= 0) {
      const target = parameters[trackingTargetIndex].value;
      const detector = parameters.find((e) => e.name === "detector")?.value;
      parameters.splice(trackingTargetIndex, 1);

      const classes = OBJECT_TRACKER_CLASSES_BY_TARGET[target]?.[detector];
      if (classes) {
        parameters.push({ name: "classes", value: classes, group: "detector_params" });
      }
    }
  }

  // `hidden` always means "not applicable to the current selection" (e.g.
  // kpi_computation's format-dependent tracking_data_id / bytetrack_run_id /
  // calibration_id, or object_tracker's detector-dependent params) -- such
  // entries are dropped entirely rather than submitted with a stale/empty
  // value, so the backend falls back to its own defaults / conditional logic.
  // Parameters additionally tagged with `group` (e.g. object_tracker's
  // detector_params / tracker_params) are bundled into a single nested
  // object under that group name instead of being submitted individually.
  const grouped = {};
  const ungrouped = [];
  for (const e of parameters) {
    if (e.hidden) continue;
    if (e.group) {
      grouped[e.group] = grouped[e.group] || {};
      grouped[e.group][e.name] = e.value;
    } else {
      ungrouped.push(e);
    }
  }

  parameters = ungrouped.map((e) => {
    if ("file" in e) {
      return { name: e.name, file: e.file };
    } else {
      return { name: e.name, value: e.value };
    }
  });
  for (const [name, value] of Object.entries(grouped)) {
    parameters.push({ name, value });
  }

  for (const video of props.videoIds) {
    const video_params = [];
    for (const param of parameters) {
      if (param.name === "shot_timeline_id" || param.name == "scalar_timeline_id") {
        video_params.push({
          name: param.name,
          value: param.value.timeline_ids[param.value.video_ids.indexOf(video)],
        });
      } else if (param.name === "timeline_ids") {
        video_params.push({
          name: param.name,
          value: param.value.map((t) => t.timeline_ids[t.video_ids.indexOf(video)]),
        });
      } else {
        video_params.push(param);
      }
    }

    pluginRunStore.submit({ plugin, parameters: video_params, videoId: video }).then(() => {
      dialog.value = false;
    });
  }
};

watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
    if (!value) {
      window.dispatchEvent(new Event("plugin-overview-closed"));
    }
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

const opened = ref([]);
watch(
  () => tutorialStore.currentStepId,
  (stepId) => {
    if (stepId === "modal-plugin-select") {
      opened.value = [7];
    }
  }
);
watch(
  () => tutorialStore.tutorialActivePluginId,
  (pluginId) => {
    if (pluginId !== null) {
      const groupId = Math.floor(pluginId / 100);
      if (!opened.value.includes(groupId)) {
        opened.value = [...opened.value, groupId];
      }
      activeNode.value = [pluginId];
    }
  }
);
watch(
  () => tutorialStore.tutorialPluginGroupOpen,
  (groupId) => {
    if (groupId !== null && !opened.value.includes(groupId)) {
      opened.value = [...opened.value, groupId];
    }
  }
);

onMounted(() => {
  // window.dispatchEvent(new Event("plugin-overview-mounted"));
  tutorialStore.modalPluginVisible = true;
  document
    .querySelector("#v-list-group--id-7")
    .parentElement.setAttribute("data-tour", "plugin-object-tracking-overview");
});

onBeforeUnmount(() => {
  tutorialStore.modalPluginVisible = false;
});
</script>
