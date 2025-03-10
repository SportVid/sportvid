<template>
  <div>
    <template v-for="parameter in parameters">
      <v-text-field
        v-model="parameter.value"
        :label="parameter.text"
        v-if="parameter.field == 'text_field'"
        :key="parameter.name"
      />

      <v-select
        v-model="parameter.value"
        :items="parameter.items"
        :label="parameter.text"
        v-if="parameter.field == 'select_options'"
        :key="parameter.name"
      />

      <v-select
        v-model="parameter.value"
        :items="shot_timelines"
        :label="parameter.text"
        :hint="parameter.hint"
        item-text="name"
        item-value="ids"
        v-if="parameter.field == 'select_timeline'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
      />

      <v-select
        v-model="parameter.value"
        :items="scalar_timelines"
        :label="parameter.text"
        :hint="parameter.hint"
        item-text="name"
        item-value="ids"
        v-if="parameter.field == 'select_scalar_timelines' && scalar_timelines.length > 0"
        :key="parameter.name"
        multiple
        persistent-hint
      />

      <v-select
        v-model="parameter.value"
        :items="scalar_timelines"
        :label="parameter.text"
        :hint="parameter.hint"
        item-text="name"
        item-value="ids"
        v-if="parameter.field == 'select_scalar_timeline' && scalar_timelines.length > 0"
        :key="parameter.name"
        persistent-hint
      />

      <div v-if="parameter.field == 'slider'" :key="parameter.name">
        <v-row v-if="parameter.hint_left && parameter.hint_right">
          <v-col cols="3" style="display: flex; justify-content: flex-end">
            {{ parameter.hint_left }}
          </v-col>

          <v-col cols="6">
            <v-slider
              v-model="parameter.value"
              :min="parameter.min"
              :max="parameter.max"
              :step="parameter.step"
              :value="parameter.default"
              :disabled="parameter.disabled"
              :hint="parameter.hint"
              thumb-label="always"
              persistent-hint
            />
          </v-col>
          <v-col cols="3">{{ parameter.hint_right }}</v-col>
        </v-row>

        <v-slider
          v-else
          v-model="parameter.value"
          :label="parameter.text"
          :min="parameter.min"
          :max="parameter.max"
          :step="parameter.step"
          :value="parameter.default"
          :disabled="parameter.disabled"
          :hint="parameter.hint"
          thumb-label="always"
          persistent-hint
        />
      </div>

      <div v-if="parameter.field == 'buttongroup'" :key="parameter.name" class="mt-8">
        <p class="mb-2">
          {{ parameter.text }}
        </p>
        <v-btn-toggle
          v-model="parameter.value"
          :label="parameter.text"
          tile
          group
          mandatory
          class="ml-n2"
        >
          <v-btn
            v-for="button in parameter.buttons"
            :key="button"
            elevation="2"
            class="mx-2 my-2"
            dark
            color="primary"
          >
            {{ button }}
          </v-btn>
        </v-btn-toggle>
      </div>

      <div v-if="parameter.field == 'image_input'" :key="parameter.name">
        <v-file-input
          v-model="parameter.file"
          :label="parameter.text"
          :hint="parameter.hint"
          accept="image/jpeg"
          persistent-hint
          filled
          prepend-icon=" mdi-camera"
        />
      </div>

      <div v-if="parameter.field == 'csv_input'" :key="parameter.name">
        <v-file-input
          v-model="parameter.file"
          :label="parameter.text"
          :hint="parameter.hint"
          accept="text/csv"
          persistent-hint
          filled
          prepend-icon=" mdi-file-delimited-outline"
        />
      </div>

      <div v-if="parameter.field == 'checkbox'" :key="parameter.name">
        <v-checkbox
          v-model="parameter.value"
          :label="parameter.text"
          :hint="parameter.hint"
          hide-details
          density="compact"
          class="ml-2 checkbox-label-spacing"
        />
      </div>
    </template>
  </div>
</template>

<script>
import { mapStores } from "pinia";
import { useTimelineStore } from "../stores/timeline";
import { usePluginRunResultStore } from "../stores/plugin_run_result";

export default {
  props: ["parameters", "videoIds"],
  methods: {
    groupTimelines(timelines) {
      let timelinesGroups = {};
      for (const timeline of timelines) {
        if (!(timeline.name in timelinesGroups)) {
          timelinesGroups[timeline.name] = {
            name: timeline.name,
            ids: {
              timeline_ids: [],
              video_ids: [],
            },
          };
        } else if (timelinesGroups[timeline.name].ids.video_ids.indexOf(timeline.video_id) >= 0) {
          continue;
        }
        timelinesGroups[timeline.name].ids.timeline_ids.push(timeline.id);
        timelinesGroups[timeline.name].ids.video_ids.push(timeline.video_id);
      }
      return Object.values(timelinesGroups).filter(
        (t) => t.ids.video_ids.length == this.videoIds.length
      );
    },
  },
  computed: {
    shot_timelines() {
      let timelines = this.timelineStore.all.filter(
        (timeline) => timeline.type == "ANNOTATION" && this.videoIds.indexOf(timeline.video_id) >= 0
      );
      return this.groupTimelines(timelines);
    },
    scalar_timelines() {
      // this.timelineStore.all.filter((t) => t.type === "PLUGIN_RESULT").forEach(element => {
      //   console.log(element.name)
      //   console.log(element.plugin)
      // });
      let timelines = this.timelineStore.all.filter(
        (t) =>
          t.type === "PLUGIN_RESULT" &&
          t.plugin &&
          t.plugin.type == "SCALAR" &&
          this.videoIds.indexOf(t.video_id) >= 0
      );
      timelines = this.groupTimelines(timelines);

      return timelines;
    },
    ...mapStores(useTimelineStore, usePluginRunResultStore),
  },
};
</script>

<style>
.checkbox-label-spacing .v-label {
  margin-left: 6px;
}
</style>
