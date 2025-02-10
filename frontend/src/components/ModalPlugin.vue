<template>
  <v-dialog v-model="dialog" max-width="90%" style="height: 85vh;">
    <v-card>
      <v-toolbar color="primary" dark class="pl-4">
        {{ $t("modal.plugin.title") }}
        </v-toolbar>
      <v-card-text>
        <v-row>
          <v-col cols="3">
            <v-text-field 
              v-model="search" 
              label="Search Plugin" 
              class="searchField"
              variant="solo-filled"
              hide-details 
              clearable
              clear-icon="mdi-close-circle-outline">
            </v-text-field>

            <v-treeview
              class="mt-2"
              :items="plugins_sorted"
              :search="search"
              :active.sync="active"
              :open.sync="open"
              activatable
              style="cursor: pointer; overflow-y: scroll; height: 500px;" 
            >
              <template v-slot:prepend="{ item }">
                <v-icon v-if="!item.children || item.children.length === 0">
                  {{ item.icon }}
                </v-icon>
              </template> 
              <template v-slot:label="{ item }">
                {{ item.title }}
              </template>
            </v-treeview>
          </v-col>

          <v-divider vertical></v-divider>

          <v-col cols="9">
            <div 
              v-if="!selected" 
              class="text-h6 text-grey font-weight-light" 
              style="text-align: center; height: 60vh"
            >
              {{ $t("modal.plugin.search.select") }}
            </div>
            <v-card 
              v-else 
              :key="selected.id" 
              class="mx-auto overflow-y-auto" 
              style="max-height: calc(80vh - 50px);"
              flat
            >
              <v-card-title class="mb-0"> {{ selected.name }} </v-card-title>
              <!-- <v-card-text>
                <div 
                  class="" 
                  style="padding-bottom: 2em;" 
                  v-html="selected.description"
                ></div>
                <Parameters 
                  :parameters="selected.parameters" 
                  :videoIds="videoIds"
                ></Parameters>
                <v-expansion-panels 
                  v-if="selected.optional_parameters && selected.optional_parameters.length > 0"
                >
                  <v-expansion-panel>
                    <v-expansion-panel-header expand-icon="mdi-menu-down">
                      Advanced Options
                    </v-expansion-panel-header>

                    <v-expansion-panel-content>
                      <Parameters 
                        :parameters="selected.optional_parameters" 
                        :videoIds="videoIds"
                      ></Parameters>
                    </v-expansion-panel-content>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-card-text> -->
            </v-card>
            <v-row>
                <v-spacer></v-spacer>
                  <v-btn 
                  :disabled="!selected" 
                  @click="runPlugin(
                    selected.plugin,
                    selected.parameters,
                    selected.optional_parameters
                  )"
                >
                  {{ $t("modal.plugin.run") }}
                </v-btn>
                <v-btn @click="dialog = false">{{ $t("modal.plugin.close") }}</v-btn>
              </v-row>
          </v-col>
        </v-row>        
      </v-card-text>      
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, reactive, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { mapStores } from "pinia";
import { usePluginRunStore } from "@/stores/plugin_run";
import Parameters from "./Parameters.vue";

export default {
  components: { Parameters },
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    videoIds: Array
  },
  setup(props, { emit }) {
    const dialog = ref(props.modelValue);
    const { t } = useI18n();
    const search = ref(null);
    const open = ref([1, 2]);
    const active = ref([]);

    const plugins = reactive([
      {
        id: 1,
        title: t("modal.plugin.groups.audio"),
        children: [
          {
            title: t("modal.plugin.audio_rms.plugin_name"),
            description: t("modal.plugin.audio_rms.plugin_description"),
            icon: "mdi-waveform",
            plugin: "audio_rms",
            id: 101,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.audio_rms.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1000,
                max: 24000,
                value: 8000,
                step: 1000,
                name: "sr",
                text: t("modal.plugin.audio_waveform.sr"),
              },
            ],
          },
          {
            title: t("modal.plugin.audio_frequency.plugin_name"),
            description: t("modal.plugin.audio_frequency.plugin_description"),
            icon: "mdi-waveform",
            plugin: "audio_freq",
            id: 102,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.audio_frequency.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1000,
                max: 24000,
                value: 8000,
                step: 1000,
                name: "sr",
                text: t("modal.plugin.audio_frequency.sr"),
              },
              {
                field: "slider",
                min: 64,
                max: 512,
                value: 256,
                step: 64, // TODO: only valid for values with power of 2
                name: "n_fft",
                text: t("modal.plugin.audio_frequency.n_fft"),
              },
            ],
          },
          {
            title: t("modal.plugin.audio_waveform.plugin_name"),
            description: t("modal.plugin.audio_waveform.plugin_description"),
            icon: "mdi-waveform",
            plugin: "audio_amp",
            id: 103,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.audio_waveform.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1000,
                max: 24000,
                value: 8000,
                step: 1000,
                name: "sr",
                text: t("modal.plugin.audio_waveform.sr"),
              },
            ],
          },
          {
            title: t("modal.plugin.whisper.plugin_name"),
            description: t("modal.plugin.whisper.plugin_description"),
            icon: "mdi-waveform",
            plugin: "whisper",
            id: 104,
            parameters: [],
            optional_parameters: [],
          },
        ],
      },
      {
        id: 2,
        title: t("modal.plugin.groups.face"),
        children: [
          {
            title: t("modal.plugin.face_clustering.plugin_name"),
            description: t("modal.plugin.face_clustering.plugin_description"),
            icon: "mdi-ungroup",
            plugin: "face_clustering",
            id: 201,
            parameters: [
              {
                field: "slider",
                min: 0.3,
                max: 0.7,
                value: 0.5,
                step: 0.01,
                name: "cluster_threshold",
                hint_right: t("modal.plugin.face_clustering.threshold.hint_right"),
                hint_left: t("modal.plugin.face_clustering.threshold.hint_left"),
              },
              {
                field: "slider",
                min: 1,
                max: 100,
                value: 50,
                step: 1,
                name: "max_cluster",
                hint_right: t("modal.plugin.face_clustering.max_cluster.hint_right"),
                hint_left: t("modal.plugin.face_clustering.max_cluster.hint_left"),
              },
              {
                field: "slider",
                min: 1,
                max: 100,
                value: 20,
                step: 1,
                name: "max_samples_per_cluster",
                hint_right: t("modal.plugin.face_clustering.max_faces.hint_right"),
                hint_left: t("modal.plugin.face_clustering.max_faces.hint_left"),
              },
              {
                field: "slider",
                min: 0,
                max: 1.0,
                value: 0.1,
                step: 0.05,
                name: "min_face_height",
                hint_right: t("modal.plugin.face_clustering.min_face_height.hint_right"),
                hint_left: t("modal.plugin.face_clustering.min_face_height.hint_left"),
              },
            ],
            optional_parameters: [
              {
                field: "select_options",
                text: t("modal.plugin.face_clustering.clustering_method_name"),
                hint: t("modal.plugin.face_clustering.clustering_method_hint"),
                items: ["Agglomerative", "DBScan"],
                name: "clustering_method",
                value: "DBScan"
              },
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t("modal.plugin.face_identification.plugin_name"),
            description: t("modal.plugin.face_identification.plugin_description"),
            icon: "mdi-account-search",
            plugin: "insightface_identification",
            id: 202,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t(
                  "modal.plugin.face_identification.timeline_name"
                ),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "image_input",
                file: null,
                name: "query_images",
                text: t(
                  "modal.plugin.face_identification.query_images"
                ),
                hint: t(
                  "modal.plugin.face_identification.query_images_hint"
                ),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t("modal.plugin.faceemotion.plugin_name"),
            description: t("modal.plugin.faceemotion.plugin_description"),
            icon: "mdi-emoticon-happy-outline",
            plugin: "deepface_emotion",
            id: 203,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.faceemotion.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_timeline",
                name: "shot_timeline_id",
                // value: this.shot_timelines_names[0],
                // items: this.shot_timelines_names,
                text: t("modal.plugin.shot_timeline_name"),
                hint: t("modal.plugin.shot_timeline_hint"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
              {
                field: "slider",
                min: 24,
                max: 256,
                value: 48,
                step: 8,
                name: "min_facesize",
                text: t("modal.plugin.faceemotion.min_facesize"),
                disabled: true,
              },
            ],
          },
          // {
          //   title: t("modal.plugin.facesize.plugin_name"),
          //   icon: "mdi-face-recognition",
          //   plugin: "insightface_facesize",
          //   id: 204,
          //   parameters: [
          //     {
          //       field: "text_field",
          //       name: "timeline",
          //       value: t("modal.plugin.facesize.timeline_name"),
          //       text: t("modal.plugin.timeline_name"),
          //     },
          //     {
          //       field: "select_timeline",
          //       name: "shot_timeline_id",
          //       // value: this.shot_timelines_names[0],
          //       // items: this.shot_timelines_names,
          //       text: t("modal.plugin.shot_timeline_name"),
          //       hint: t("modal.plugin.shot_timeline_hint"),
          //     },
          //   ],
          //   optional_parameters: [
          //     {
          //       field: "slider",
          //       min: 1,
          //       max: 10,
          //       value: 2,
          //       step: 1,
          //       name: "fps",
          //       text: t("modal.plugin.fps"),
          //     },
          //   ],
          // },
        ],
      },
      {
        id: 3,
        title: t("modal.plugin.groups.color"),
        children: [
          {
            title: t("modal.plugin.color_analysis.plugin_name"),
            description: t("modal.plugin.color_analysis.plugin_description"),
            icon: "mdi-palette",
            plugin: "color_analysis",
            id: 301,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.color_analysis.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "slider",
                min: 1,
                max: 8,
                value: 1,
                step: 1,
                name: "k",
                text: t("modal.plugin.color_analysis.slider"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
              {
                field: "slider",
                min: 24,
                max: 128,
                value: 48,
                step: 4,
                name: "max_resolution",
                text: t("modal.plugin.color_analysis.max_resolution"),
              },
              {
                field: "slider",
                min: 5,
                max: 25,
                value: 10,
                step: 5,
                name: "max_iter",
                text: t("modal.plugin.color_analysis.max_iter"),
              },
            ],
          },
          {
            title: t(
              "modal.plugin.color_brightness_analysis.plugin_name"
            ),
            description: t("modal.plugin.color_brightness_analysis.plugin_description"),
            icon: "mdi-palette",
            plugin: "color_brightness_analysis",
            id: 302,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t(
                  "modal.plugin.color_brightness_analysis.timeline_name"
                ),
                text: t("modal.plugin.timeline_name"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
              {
                field: "checkbox",
                name: "normalize",
                text: t("modal.plugin.normalize"),
                value: true
              },
            ],
          },
        ],
      },
      {
        id: 4,
        title: t("modal.plugin.groups.identification"),
        children: [
          {
            title: t("modal.plugin.clip.plugin_name"),
            description: t("modal.plugin.clip.plugin_description"),
            icon: "mdi-eye",
            plugin: "clip",
            id: 403,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.clip.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "text_field",
                name: "search_term",
                value: "",
                text: t("modal.plugin.clip.search_term"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t("modal.plugin.clip_ontology.plugin_name"),
            description: t("modal.plugin.clip_ontology.plugin_description"),
            icon: "mdi-eye",
            plugin: "clip_ontology",
            id: 402,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.clip_ontology.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_timeline",
                name: "shot_timeline_id",
                // value: this.shot_timelines_names[0],
                // items: this.shot_timelines_names,
                text: t("modal.plugin.shot_timeline_name"),
                hint: t("modal.plugin.shot_timeline_hint"),
              },
              {
                field: "csv_input",
                file: null,
                name: "concept_csv",
                text: t("modal.plugin.clip_ontology.concepts"),
                hint: t("modal.plugin.clip_ontology.concepts_hint"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t("modal.plugin.x_clip.plugin_name"),
            description: t("modal.plugin.x_clip.plugin_description"),
            icon: "mdi-eye",
            plugin: "x_clip",
            id: 404,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.x_clip.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "text_field",
                name: "search_term",
                value: "",
                text: t("modal.plugin.x_clip.search_term"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t("modal.plugin.places_classification.plugin_name"),
            description: t("modal.plugin.places_classification.plugin_description"),
            icon: "mdi-map-marker",
            plugin: "places_classification",
            id: 401,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t(
                  "modal.plugin.places_classification.timeline_name"
                ),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_timeline",
                name: "shot_timeline_id",
                // value: this.shot_timelines_names[0],
                // items: this.shot_timelines_names,
                text: t("modal.plugin.shot_timeline_name"),
                hint: t("modal.plugin.shot_timeline_hint"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t("modal.plugin.place_clustering.plugin_name"),
            description: t("modal.plugin.place_clustering.plugin_description"),
            icon: "mdi-ungroup",
            plugin: "place_clustering",
            id: 405,
            parameters: [
              {
                field: "select_timeline",
                name: "shot_timeline_id",
                text: t("modal.plugin.shot_timeline_name"),
                hint: t("modal.plugin.shot_timeline_hint"),
              },
  //                {
  //                  field: "select_options",
  //                  text: t("modal.plugin.place_clustering.encoder_name"),
  //                  hint: t("modal.plugin.place_clustering.encoder_hint"),
  //                  items: ["CLIP", "Places"],
  //                  name: "encoder",
  //                },
              {
                field: "slider",
                min: 0.05,
                max: 0.3,
                value: 0.15,
                step: 0.01,
                name: "cluster_threshold",
                hint_right: t("modal.plugin.place_clustering.threshold.hint_right"),
                hint_left: t("modal.plugin.place_clustering.threshold.hint_left"),
              },
              {
                field: "slider",
                min: 1,
                max: 100,
                value: 50,
                step: 1,
                name: "max_cluster",
                hint_right: t("modal.plugin.place_clustering.max_cluster.hint_right"),
                hint_left: t("modal.plugin.place_clustering.max_cluster.hint_left"),
              },
            ],
            optional_parameters: [
              {
                field: "select_options",
                text: t("modal.plugin.place_clustering.clustering_method_name"),
                hint: t("modal.plugin.place_clustering.clustering_method_hint"),
                items: ["Agglomerative", "DBScan"],
                name: "clustering_method",
                value: "DBScan"
              }
            ],
          },
          {
            title: t("modal.plugin.blip.plugin_name"),
            description: t("modal.plugin.blip.plugin_description"),
            icon: "mdi-eye",
            plugin: "blip_vqa",
            id: 406,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.blip.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_timeline",
                name: "shot_timeline_id",
                // value: this.shot_timelines_names[0],
                // items: this.shot_timelines_names,
                text: t("modal.plugin.shot_timeline_name"),
                hint: t("modal.plugin.shot_timeline_hint"),
              },
              {
                field: "text_field",
                name: "query_term",
                value: "",
                text: t("modal.plugin.blip.search_term"),
              },
            ],
            optional_parameters: [
            ],
          },
          {
            title: t("modal.plugin.ocr.plugin_name"),
            icon: "mdi-text-shadow",
            plugin: "ocr_video_detector_onnx",
            id: 407,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.ocr.timeline_name"),
                text: t("modal.plugin.ocr.timeline_name"),
              },
              {
                field: "text_field",
                name: "search_term",
                value: "",
                text: t("modal.plugin.ocr.search_term"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
        ],
      },
      {
        id: 5,
        title: t("modal.plugin.groups.shot"),
        children: [
          {
            title: t("modal.plugin.shot_detection.plugin_name"),
            description: t("modal.plugin.shot_detection.plugin_description"),
            icon: "mdi-arrow-expand-horizontal",
            plugin: "shotdetection",
            id: 501,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.shot_detection.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t("modal.plugin.shot_density.plugin_name"),
            description: t("modal.plugin.shot_density.plugin_description"),
            icon: "mdi-sine-wave",
            plugin: "shot_density",
            id: 503,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.shot_density.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_timeline",
                name: "shot_timeline_id",
                text: t("modal.plugin.shot_density.input_timeline"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 60,
                value: 10,
                step: 1,
                name: "bandwidth",
                text: t("modal.plugin.shot_density.bandwidth"),
              },
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 10,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t(
              "modal.plugin.shot_type_classification.plugin_name"
            ),
            description: t("modal.plugin.shot_type_classification.plugin_description"),
            icon: "mdi-video-switch",
            plugin: "shot_type_classification",
            id: 504,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t(
                  "modal.plugin.shot_type_classification.timeline_name"
                ),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_timeline",
                name: "shot_timeline_id",
                text: t("modal.plugin.shot_timeline_name"),
                hint: t("modal.plugin.shot_timeline_hint"),
              },
            ],
            optional_parameters: [
              {
                field: "slider",
                min: 1,
                max: 10,
                value: 2,
                step: 1,
                name: "fps",
                text: t("modal.plugin.fps"),
              },
            ],
          },
          {
            title: t("modal.plugin.shot_scalar_annotation.plugin_name"),
            description: t("modal.plugin.shot_scalar_annotation.plugin_description"),
            icon: "mdi-label-outline",
            plugin: "shot_scalar_annotation",
            id: 505,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t(
                  "modal.plugin.shot_scalar_annotation.timeline_name"
                ),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_timeline",
                name: "shot_timeline_id",
                text: t("modal.plugin.shot_timeline_name"),
                hint: t("modal.plugin.shot_timeline_hint"),
              },
              {
                field: "select_scalar_timeline",
                name: "scalar_timeline_id",
                text: t("modal.plugin.scalar_timeline_name"),
                hint: t("modal.plugin.scalar_timeline_hint"),
              },
            ],
            optional_parameters: [],
          },
          {
            title: t("modal.plugin.thumbnail.plugin_name"),
            description: t("modal.plugin.thumbnail.plugin_description"),
            icon: "mdi-image-multiple",
            plugin: "thumbnail",
            id: 502,
            parameters: [],
            optional_parameters: [],
          },
        ],
      },
      {
        id: 6,
        title: t("modal.plugin.groups.aggregation"),
        children: [
          {
            title: t("modal.plugin.aggregation.plugin_name"),
            description: t("modal.plugin.aggregation.plugin_description"),
            icon: "mdi-sigma",
            plugin: "aggregate_scalar",
            id: 601,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.aggregation.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_scalar_timelines",
                name: "timeline_ids",
                text: t("modal.plugin.scalar_timeline_name"),
                hint: t("modal.plugin.scalar_timeline_hint"),
              },
              {
                field: "buttongroup",
                text: t("modal.plugin.aggregation.method"),
                name: "aggregation",
                value: 0,
                buttons: [
                  t("modal.plugin.aggregation.logical_or"),
                  t("modal.plugin.aggregation.logical_and"),
                  t("modal.plugin.aggregation.mean"),
                  t("modal.plugin.aggregation.prod"),
                ],
              },
            ],
            optional_parameters: [],
          }, {
            title: t("modal.plugin.invert.plugin_name"),
            description: t("modal.plugin.invert.plugin_description"),
            icon: "mdi-numeric-negative-1",
            plugin: "invert_scalar",
            id: 602,
            parameters: [
              {
                field: "text_field",
                name: "timeline",
                value: t("modal.plugin.invert.timeline_name"),
                text: t("modal.plugin.timeline_name"),
              },
              {
                field: "select_scalar_timeline",
                name: "scalar_timeline_id",
                text: t("modal.plugin.scalar_timeline_name"),
                hint: t("modal.plugin.scalar_timeline_hint"),
              },
            ],
            optional_parameters: [],
          },
        ],
      },
    ]);

    const plugins_sorted = computed(() => {
      return plugins.slice(0).sort((a, b) => a.title.localeCompare(b.title));
    });

    const selected = computed(() => {
      if (!active.value.length) return undefined;

      const id = active.value[0];
      if (id < 100) return undefined;

      let plugin_group = plugins.find((group) => group.id === parseInt(id / 100));
      let plugin = plugin_group?.children.find((plugin) => plugin.id === id);

      return plugin;
    });

    const { pluginRunStore } = mapStores(usePluginRunStore);

    const runPlugin = async (plugin, parameters, optional_parameters) => {
      parameters = [...parameters, ...optional_parameters];
      parameters = parameters.map((e) => {
        if ("file" in e) {
          return { name: e.name, file: e.file };
        } else {
          return { name: e.name, value: e.value };
        }
      });

      for (const video of props.videoIds) {
        const video_params = [];
        for (const param of parameters) {
          if (param.name === 'shot_timeline_id' || param.name == 'scalar_timeline_id') {
            video_params.push({
              name: param.name,
              value: param.value.timeline_ids[param.value.video_ids.indexOf(video)]
            });
          } else if (param.name === 'timeline_ids') {
            video_params.push({
              name: param.name,
              value: param.value.map(t => t.timeline_ids[t.video_ids.indexOf(video)])
            })
          } else {
            video_params.push(param);
          }
        }

        pluginRunStore
          .submit({ plugin, parameters: video_params, videoId: video })
          .then(() => {
            dialog.value = false;
          });
      }
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
      search,
      open,
      active,
      plugins_sorted,
      selected,
      runPlugin
    };
  }
};
</script>

<style>
div.tabs-left [role="tab"] {
  justify-content: flex-start;
}
</style>
