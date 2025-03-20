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
        item-title="name"
        item-value="ids"
        v-if="parameter.field == 'select_timeline'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
      />

      <v-select
        v-model="parameter.value"
        :items="position_data_teams"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_pos_data_team'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
      />

      <v-select
        v-model="parameter.value"
        :items="scalar_timelines"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
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
        item-title="name"
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

<script setup>
import { computed } from "vue";
import { useTimelineStore } from "../stores/timeline";
import { usePluginRunResultStore } from "../stores/plugin_run_result";
import { useMarkerStore } from "../stores/marker";

const props = defineProps({
  parameters: Array,
  videoIds: Array,
});

const timelineStore = useTimelineStore();
const pluginRunResultStore = usePluginRunResultStore();
const markerStore = useMarkerStore();

const groupTimelines = (timelines) => {
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
    (t) => t.ids.video_ids.length == props.videoIds.length
  );
};

const shot_timelines = computed(() => {
  let timelines = timelineStore.all.filter(
    (timeline) => timeline.type == "ANNOTATION" && props.videoIds.indexOf(timeline.video_id) >= 0
  );

  return groupTimelines(timelines);
});

const scalar_timelines = computed(() => {
  let timelines = timelineStore.all.filter(
    (t) =>
      t.type === "PLUGIN_RESULT" &&
      t.plugin &&
      t.plugin.type == "SCALAR" &&
      props.videoIds.indexOf(t.video_id) >= 0
  );
  timelines = groupTimelines(timelines);
  return timelines;
});

const position_data_teams = computed(() => {
  const teams = new Set(markerStore.positions.flat().map((player) => player.team));
  return [
    { name: "Both Teams", id: "both" },
    ...[...teams].map((team) => ({
      name: `Team ${team.charAt(0).toUpperCase() + team.slice(1)}`,
      id: team,
    })),
  ];
});
</script>

<style>
.checkbox-label-spacing .v-label {
  margin-left: 6px;
}
</style>
