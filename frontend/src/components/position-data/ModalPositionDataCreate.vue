<template>
  <v-dialog v-model="dialog" width="60%">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">{{ $t("position_data.generate.create") }}</v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="max-height: 70vh; overflow-y: auto">
        <div style="padding-bottom: 2em" v-html="$t('position_data.generate.create_description')" />

        <!-- Create/select-for-editing a calibration asset -- full width, same buttons+flow as
             Parameters.vue's "select_calibration" field (Complex-mode DLT modal) uses, just
             laid out separately here so the actual picker below can live in its own column
             instead of being stuck directly underneath these. -->
        <div class="d-flex ga-2 mb-4" data-tour="dlt-calibration-create-select">
          <v-btn
            variant="outlined"
            prepend-icon="mdi-plus"
            class="flex-grow-1"
            @click="onCreateCalibration"
          >
            {{ $t("calibration_asset.create") }}
          </v-btn>
          <v-btn
            variant="outlined"
            prepend-icon="mdi-pencil"
            class="flex-grow-1"
            @click="showCalibrationSelectForEdit = true"
          >
            {{ $t("calibration_asset.select") }}
          </v-btn>
        </div>
        <ModalCalibrationAssetSelect
          v-if="showCalibrationSelectForEdit"
          v-model="showCalibrationSelectForEdit"
          @selected="onSelectCalibration"
        />

        <v-divider class="my-6" />

        <v-row class="mx-2 mt-2">
          <!-- Left: which saved asset the DLT calibration run below uses, and the
               player-tracking source (new run vs. reusing an existing finished one). -->
          <v-col cols="12" md="6">
            <v-select
              v-model="calibrationId"
              :items="calibrationAssets"
              :label="$t('modal.plugin.calibration_static_dlt.calibration_id')"
              item-title="name"
              item-value="id"
              persistent-hint
              variant="underlined"
              data-tour="posdata-create-calibration-select"
            />

            <v-select
              v-model="playerTrackingSelection"
              :items="playerTrackingItems"
              :label="$t('position_data.generate.player_tracking')"
              item-title="title"
              item-value="value"
              persistent-hint
              variant="underlined"
              data-tour="posdata-create-player-tracking"
            />
          </v-col>

          <!-- Right: everything optional layered on top of that. -->
          <v-col cols="12" md="6" class="pl-md-8">
            <v-checkbox
              v-model="ballTracking"
              :label="$t('position_data.generate.ball_tracking')"
              hide-details
              density="compact"
              data-tour="posdata-create-ball-tracking"
            />
            <div class="d-flex align-center">
              <v-checkbox
                v-model="teamAssignment"
                :label="$t('position_data.generate.team_assignment')"
                hide-details
                density="compact"
                data-tour="posdata-create-team-assignment"
              />
              <v-tooltip v-if="playerTrackingSelection === 'new'" location="top">
                <template #activator="{ props: tooltipProps }">
                  <v-icon
                    v-bind="tooltipProps"
                    icon="mdi-information-outline"
                    size="small"
                    class="text-grey ml-1"
                  />
                </template>
                {{ $t("position_data.generate.waits_for_player_tracking") }}
              </v-tooltip>
            </div>
            <div class="d-flex align-center">
              <v-checkbox
                v-model="reIdentification"
                :label="$t('position_data.generate.re_identification')"
                hide-details
                density="compact"
                data-tour="posdata-create-re-identification"
              />
              <v-tooltip v-if="playerTrackingSelection === 'new'" location="top">
                <template #activator="{ props: tooltipProps }">
                  <v-icon
                    v-bind="tooltipProps"
                    icon="mdi-information-outline"
                    size="small"
                    class="text-grey ml-1"
                  />
                </template>
                {{ $t("position_data.generate.waits_for_player_tracking") }}
              </v-tooltip>
            </div>
          </v-col>
        </v-row>

        <v-row class="mt-4">
          <v-spacer />
          <v-btn :disabled="!calibrationId" data-tour="posdata-create-run" @click="runPlugins">
            {{ $t("button.run_plugins") }}
          </v-btn>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>

  <ModalCalibrationAssetCreate v-if="showCalibrationCreate" v-model="showCalibrationCreate" />
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useCalibrationCreateFlow } from "@/composables/useCalibrationCreateFlow";
import { useObjectTrackerPlayerRuns } from "@/composables/useObjectTrackerPlayerRuns";
import {
  dltParams,
  objectTrackerParams,
  teamClusteringParams,
  osnetReidParams,
  submitPlugin,
} from "@/composables/usePluginParams";
import ModalCalibrationAssetCreate from "@/components/calibration-asset/ModalCalibrationAssetCreate.vue";
import ModalCalibrationAssetSelect from "@/components/calibration-asset/ModalCalibrationAssetSelect.vue";

const { t } = useI18n();
const pluginRunResultStore = usePluginRunResultStore();
const calibrationAssetStore = useCalibrationAssetStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  videoId: [String, Number],
});

const emit = defineEmits(["update:modelValue"]);

const dialog = ref(props.modelValue);
watch(
  () => dialog.value,
  (value) => emit("update:modelValue", value)
);
watch(
  () => props.modelValue,
  (value) => {
    if (value) dialog.value = true;
  }
);

const { showCalibrationCreate, onCreateCalibration, onSelectCalibration } =
  useCalibrationCreateFlow(dialog);

// This flow never exposes per-plugin parameters -- every run below submits with the same
// defaults each plugin's own (Complex-mode) modal starts with, see usePluginParams.js.
// Destructured (rather than kept as `dlt.parameters`) so <script setup>'s template compiler
// auto-unwraps it -- a nested `dlt.parameters` access in the template stays a Ref object
// instead of the array Parameters.vue expects (see the "$props.parameters.filter is not a
// function" crash this used to cause).
const { parameters: dltParameters, optionalParameters: dltOptionalParameters } = dltParams();
// Writable so the split-out v-select below (see template) can drive the same underlying
// dltParameters field submitPlugin("calibration_static_dlt", ...) reads from -- same value,
// just no longer rendered together with the create/select-for-editing buttons above it.
const calibrationId = computed({
  get: () => dltParameters.value.find((p) => p.name === "calibration_id")?.value,
  set: (value) => {
    const field = dltParameters.value.find((p) => p.name === "calibration_id");
    if (field) field.value = value;
  },
});
const calibrationAssets = computed(() =>
  Object.values(calibrationAssetStore.calibrationAssetsList)
);
const showCalibrationSelectForEdit = ref(false);

onMounted(() => {
  calibrationAssetStore.loadCalibrationAssetsList();
  // Needed so useObjectTrackerPlayerRuns can tell finished player- from ball-tracking runs
  // apart (via each run's result name) -- same call Parameters.vue's own onMounted makes,
  // duplicated here since this modal no longer renders <Parameters> at all.
  pluginRunResultStore.fetchForVideo({ videoId: props.videoId });
});

const { objectTrackerPlayerRuns } = useObjectTrackerPlayerRuns();
const playerTrackingSelection = ref("new");
const playerTrackingItems = computed(() => [
  { title: t("position_data.generate.new_run"), value: "new" },
  ...objectTrackerPlayerRuns.value.map((run) => ({ title: run.name, value: run.id })),
]);

const ballTracking = ref(false);
const teamAssignment = ref(false);
const reIdentification = ref(false);

// paramsFactory functions (objectTrackerParams/teamClusteringParams/osnetReidParams) call
// useI18n() internally, which -- like any composable relying on getCurrentInstance() -- only
// works while a component's setup() is still running. Calling them lazily from inside
// runPlugins()/a click handler (as this used to) crashes with "Must be called at the top of a
// `setup` function". So every run this modal can submit is built once, right here at setup
// time, and only *submitted* (read via .value) later on click.
const playerTrackerParams = objectTrackerParams(); // tracking_target defaults to "player"
const ballTrackerParams = objectTrackerParams();
const ballTargetField = ballTrackerParams.parameters.value.find(
  (p) => p.name === "tracking_target"
);
if (ballTargetField) ballTargetField.value = "ball";

const teamClusteringParamsObj = teamClusteringParams();
const osnetReidParamsObj = osnetReidParams();

const submitObjectTracker = (params) =>
  submitPlugin(
    "object_tracker",
    [...params.parameters.value, ...params.optionalParameters.value],
    props.videoId
  );

const submitWithObjectTrackerId = (params, plugin, objectTrackerId) => {
  const idField = params.parameters.value.find((p) => p.name === "object_tracker_id");
  if (idField) idField.value = objectTrackerId;
  return submitPlugin(
    plugin,
    [...params.parameters.value, ...params.optionalParameters.value],
    props.videoId
  );
};

// Team Assignment/Re-ID need a *finished* player-tracking run's id as input -- submitting them
// alongside a still-running object_tracker used to crash on the backend, so this used to wait
// client-side for it to reach DONE first. That's now handled server-side instead: the
// run_plugin celery task itself reschedules team_clustering/osnet_reid via Celery's own retry
// until their object_tracker_id dependency is DONE (see plugin_manager.py's run_plugin task) --
// so here it's safe to just submit them immediately, right alongside a freshly-started Object
// Tracker run, same as an already-finished existing run needs no special-casing either.
const runDependentPlugins = (objectTrackerId) => {
  if (!objectTrackerId) return;
  if (teamAssignment.value) {
    submitWithObjectTrackerId(teamClusteringParamsObj, "team_clustering", objectTrackerId);
  }
  if (reIdentification.value) {
    submitWithObjectTrackerId(osnetReidParamsObj, "osnet_reid", objectTrackerId);
  }
};

const runPlugins = () => {
  submitPlugin(
    "calibration_static_dlt",
    [...dltParameters.value, ...dltOptionalParameters.value],
    props.videoId
  );

  if (ballTracking.value) {
    submitObjectTracker(ballTrackerParams);
  }

  if (playerTrackingSelection.value === "new") {
    submitObjectTracker(playerTrackerParams).then((res) => {
      const newRunId = res?.plugin_run_id;
      if (!newRunId) {
        // Backend didn't hand back a plugin_run_id -- can't tell Team Assignment/Re-ID which
        // run to use, so they're skipped rather than guessed. Logged since this otherwise
        // fails silently in the UI (e.g. an out-of-date backend not returning it yet).
        if (teamAssignment.value || reIdentification.value) {
          console.error(
            "object_tracker submit response had no plugin_run_id -- skipping Team Assignment/Re-ID",
            res
          );
        }
        return;
      }
      runDependentPlugins(newRunId);
    });
  } else {
    runDependentPlugins(playerTrackingSelection.value);
  }

  dialog.value = false;
};
</script>
