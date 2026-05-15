<template>
  <div>
    <template v-for="parameter in parameters.filter((p) => !p.hidden)">
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
        :data-tour="parameter.dataTour || undefined"
      />

      <v-select
        v-model="parameter.value"
        :items="shotTimelines"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="ids"
        v-if="parameter.field == 'select_timeline'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
      />

      <div
        v-if="parameter.field == 'select_calibration'"
        :key="parameter.name"
        :data-tour="parameter.dataTour || undefined"
      >
        <div
          v-if="!parameter.dlt"
          class="d-flex ga-2 mb-6"
          data-tour="dlt-calibration-create-select"
        >
          <v-btn
            variant="outlined"
            prepend-icon="mdi-plus"
            class="flex-grow-1"
            @click="emit('create-calibration')"
          >
            {{ $t("calibration_asset.create") }}
          </v-btn>
          <v-btn
            variant="outlined"
            prepend-icon="mdi-pencil"
            class="flex-grow-1"
            @click="showModalCalibrationAssetSelectForEdit = true"
          >
            {{ $t("calibration_asset.select") }}
          </v-btn>
        </div>
        <ModalCalibrationAssetSelect
          v-if="showModalCalibrationAssetSelectForEdit"
          v-model="showModalCalibrationAssetSelectForEdit"
          @selected="onCalibrationAssetSelected"
        />
        <v-select
          v-model="parameter.value"
          :items="calibrationAssets"
          :label="parameter.text"
          :hint="parameter.hint"
          item-title="name"
          item-value="id"
          persistent-hint
          variant="underlined"
        />
      </div>

      <v-select
        v-model="parameter.value"
        :items="
          parameter.format_filter
            ? trackingDatasets.filter((d) => d.file_type === parameter.format_filter)
            : trackingDatasets
        "
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_tracking_data'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        class="mb-4"
        :data-tour="parameter.dataTour || undefined"
      />

      <v-select
        v-model="parameter.value"
        :items="bytetrackRuns"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_bytetrack_run'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        class="mb-4"
        :no-data-text="$t('modal.plugin.kpi_computation.bytetrack_run_none')"
        :data-tour="parameter.dataTour || undefined"
      />

      <v-select
        v-model="parameter.value"
        :items="positionDataTeams"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_position_data_team'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        multiple
      >
        <template v-slot:prepend-item v-if="positionDataTeams?.length > 0">
          <v-checkbox
            class="ml-4 my-n2 text-body-2"
            v-model="isPositionDataTeamSelectAll"
            @click="togglePositionDataTeamSelectAll(parameter)"
            hide-details
            ripple
          >
            <template v-slot:label>
              <span class="text-body-1">{{ $t("modal.export.position_data.teams.all") }}</span>
            </template>
          </v-checkbox>
          <v-divider />
        </template>

        <template v-slot:selection="{ item, index }">
          <v-chip v-if="index < 4" :text="item.title" />
          <v-chip v-if="index === 4" class="text-grey text-caption">
            (+{{ parameter.value.length - 4 }} others)
          </v-chip>
        </template>
      </v-select>

      <v-select
        v-model="parameter.value"
        :items="exportStore.selectablePositionDataAttributes"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_position_data_attribute'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        multiple
        class="mt-6"
        :menu-props="{ location: 'bottom', maxHeight: 250 }"
      >
        <template
          v-slot:prepend-item
          v-if="exportStore.selectablePositionDataAttributes?.length > 0"
        >
          <v-checkbox
            class="ml-4 my-n2 text-body-2"
            v-model="isPositionDataAttributeSelectAll"
            @click="togglePositionDataAttributeSelectAll(parameter)"
            hide-details
            ripple
          >
            <template v-slot:label>
              <span class="text-body-1">{{ $t("modal.export.position_data.attributes.all") }}</span>
            </template>
          </v-checkbox>
          <v-divider />
        </template>

        <template v-slot:selection="{ item, index }">
          <v-chip v-if="index < 2" :text="item.title" />
          <v-chip v-if="index === 2" class="text-grey text-caption">
            (+{{ parameter.value.length - 2 }} others)
          </v-chip>
        </template>
      </v-select>

      <v-select
        v-model="parameter.value"
        :items="kpiTeams"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_kpi_team'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        multiple
      >
        <template v-slot:prepend-item v-if="kpiTeams?.length > 0">
          <v-checkbox
            class="ml-4 my-n2 text-body-2"
            v-model="isKpiTeamSelectAll"
            @click="toggleKpiTeamSelectAll(parameter)"
            hide-details
            ripple
          >
            <template v-slot:label>
              <span class="text-body-1">{{ $t("modal.export.kpi.teams.all") }}</span>
            </template>
          </v-checkbox>
          <v-divider />
        </template>

        <template v-slot:selection="{ item, index }">
          <v-chip v-if="index < 4" :text="item.title" />
          <v-chip v-if="index === 4" class="text-grey text-caption">
            (+{{ parameter.value.length - 4 }} others)
          </v-chip>
        </template>
      </v-select>

      <v-select
        v-model="parameter.value"
        :items="kpiNameItems"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_kpi_names'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        multiple
        class="mt-6"
        :menu-props="{ location: 'bottom', maxHeight: 250 }"
      >
        <template v-slot:prepend-item v-if="kpiNameItems?.length > 0">
          <v-checkbox
            class="ml-4 my-n2 text-body-2"
            v-model="isKpiNamesSelectAll"
            @click="toggleKpiNamesSelectAll(parameter)"
            hide-details
            ripple
          >
            <template v-slot:label>
              <span class="text-body-1">{{ $t("modal.export.kpi.kpi_names.all") }}</span>
            </template>
          </v-checkbox>
          <v-divider />
        </template>

        <template v-slot:item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps" :title="undefined">
            <template #prepend="{ isSelected }">
              <v-checkbox-btn :model-value="isSelected" />
            </template>
            <template #title>
              <span v-html="item.raw.name" />
            </template>
          </v-list-item>
        </template>

        <template v-slot:selection="{ item, index }">
          <v-chip v-if="index < 2">
            <span v-html="item.raw.name" />
          </v-chip>
          <v-chip v-if="index === 2" class="text-grey text-caption">
            (+{{ parameter.value.length - 2 }} others)
          </v-chip>
        </template>
      </v-select>

      <v-select
        v-model="parameter.value"
        :items="kpiNameItemsAggregated"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_kpi_names_aggregated'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        multiple
        class="mt-6"
        :menu-props="{ location: 'bottom', maxHeight: 250 }"
      >
        <template v-slot:prepend-item v-if="kpiNameItemsAggregated?.length > 0">
          <v-checkbox
            class="ml-4 my-n2 text-body-2"
            v-model="isKpiNamesAggregatedSelectAll"
            @click="toggleKpiNamesAggregatedSelectAll(parameter)"
            hide-details
            ripple
          >
            <template v-slot:label>
              <span class="text-body-1">{{ $t("modal.export.kpi_aggregated.kpi_names.all") }}</span>
            </template>
          </v-checkbox>
          <v-divider />
        </template>

        <template v-slot:item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps" :title="undefined">
            <template #prepend="{ isSelected }">
              <v-checkbox-btn :model-value="isSelected" />
            </template>
            <template #title>
              <span v-html="item.raw.name" />
            </template>
          </v-list-item>
        </template>

        <template v-slot:selection="{ item, index }">
          <v-chip v-if="index < 2">
            <span v-html="item.raw.name" />
          </v-chip>
          <v-chip v-if="index === 2" class="text-grey text-caption">
            (+{{ parameter.value.length - 2 }} others)
          </v-chip>
        </template>
      </v-select>

      <v-select
        v-model="parameter.value"
        :items="exportStore.selectableKpiAttributes"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_kpi_attribute'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        multiple
        class="mt-6"
        :menu-props="{ location: 'bottom', maxHeight: 250 }"
      >
        <template v-slot:prepend-item v-if="exportStore.selectableKpiAttributes?.length > 0">
          <v-checkbox
            class="ml-4 my-n2 text-body-2"
            v-model="isKpiAttributeSelectAll"
            @click="toggleKpiAttributeSelectAll(parameter)"
            hide-details
            ripple
          >
            <template v-slot:label>
              <span class="text-body-1">{{ $t("modal.export.kpi.attributes.all") }}</span>
            </template>
          </v-checkbox>
          <v-divider />
        </template>

        <template v-slot:selection="{ item, index }">
          <v-chip v-if="index < 2" :text="item.title" />
          <v-chip v-if="index === 2" class="text-grey text-caption">
            (+{{ parameter.value.length - 2 }} others)
          </v-chip>
        </template>
      </v-select>

      <v-autocomplete
        v-model="parameter.value"
        v-if="parameter.field == 'select_kpi_frame'"
        type="number"
        :min="parameter.min"
        :max="parameter.max"
        :items="parameter.items"
        :label="parameter.text"
        hide-details
        class="mt-8"
        persistent-hint
        variant="underlined"
        :menu-props="{ location: 'bottom', maxHeight: 160 }"
        :style="{
          display: 'inline-block',
          width: '48%',
          marginRight: parameter.name === 'kpi_start_frame' ? '4%' : '0',
        }"
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

      <div
        v-if="parameter.field == 'slider'"
        :key="parameter.name"
        :data-tour="parameter.dataTour || undefined"
      >
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
          class="mt-4"
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
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useTimelineStore } from "@/stores/timeline";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useTopViewStore } from "@/stores/top_view";
import ModalCalibrationAssetSelect from "@/components/calibration-asset/ModalCalibrationAssetSelect.vue";
import { useExportStore } from "@/stores/export";
import { usePositionDataStore } from "@/stores/position_data";
import { useVisualizationStore } from "@/stores/visualization";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePlayerStore } from "@/stores/player";

const timelineStore = useTimelineStore();
const calibrationAssetStore = useCalibrationAssetStore();
const topViewStore = useTopViewStore();
const exportStore = useExportStore();
const positionDataStore = usePositionDataStore();
const visualizationStore = useVisualizationStore();
const pluginRunStore = usePluginRunStore();
const playerStore = usePlayerStore();

const { t } = useI18n();

const props = defineProps({
  parameters: Array,
  videoIds: Array,
});

const emit = defineEmits(["create-calibration", "select-calibration"]);

const showModalCalibrationAssetSelectForEdit = ref(false);
const onCalibrationAssetSelected = () => {
  emit("select-calibration");
};

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

const shotTimelines = computed(() => {
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

const positionDataTeams = computed(() => {
  const meta = topViewStore.metaDataTopView;
  const items = [];

  // Use precomputed lists as source of truth — they are rebuilt from actual bbox data
  // by transformBBoxToPositionDataTopView and are always up-to-date after edits.
  if (topViewStore.precomputedBallList.length > 0) {
    items.push({ id: 1, name: t("position_data.entity_kind.ball") });
  }
  if (topViewStore.precomputedRefList.length > 0) {
    items.push({ id: 2, name: t("position_data.entity_kind.ref") });
  }

  const playerTeamIds = [...new Set(topViewStore.precomputedPlayerList.map((p) => p.teamId))].sort(
    (a, b) => a - b
  );
  for (const team_id of playerTeamIds) {
    items.push({ id: team_id, name: meta?.team_ids?.[team_id]?.name ?? String(team_id) });
  }

  if (topViewStore.precomputedInactiveList.length > 0) {
    items.push({ id: 0, name: t("position_data.entity_kind.rest") });
  }

  return items.length > 0 ? items : undefined;
});

const isPositionDataTeamSelectAll = ref(false);
const togglePositionDataTeamSelectAll = (parameter) => {
  if (!isPositionDataTeamSelectAll.value) {
    parameter.value = positionDataTeams.value.map((team) => team.id);
  } else {
    parameter.value = [];
  }

  isPositionDataTeamSelectAll.value = !isPositionDataTeamSelectAll.value;
};

const isPositionDataAttributeSelectAll = ref(false);
const togglePositionDataAttributeSelectAll = (parameter) => {
  if (!isPositionDataAttributeSelectAll.value) {
    parameter.value = exportStore.selectablePositionDataAttributes.map((a) => a.id);
  } else {
    parameter.value = [];
  }

  isPositionDataAttributeSelectAll.value = !isPositionDataAttributeSelectAll.value;
};

const kpiTeams = computed(() => {
  if (!visualizationStore.kpiDataLoaded) return [];

  // Use the same source of truth as positionDataTeams — precomputedPlayerList reflects
  // the current loaded data and only contains actual player teams (tid >= 3).
  const playerTeamIds = [...new Set(topViewStore.precomputedPlayerList.map((p) => p.teamId))].sort(
    (a, b) => a - b
  );

  const kpiMeta = visualizationStore.kpiMetaTeamIds;
  const meta = topViewStore.metaDataTopView;
  return playerTeamIds.map((team_id) => ({
    id: team_id,
    name:
      kpiMeta?.[team_id]?.name ??
      kpiMeta?.[String(team_id)]?.name ??
      meta?.team_ids?.[team_id]?.name ??
      String(team_id),
  }));
});

const kpiNameItems = computed(() =>
  (visualizationStore.kpiNames || []).map((name) => ({
    id: name,
    name: t(`visualization.kpi.kpi_selection.${name}`, name),
  }))
);

// Aggregated selection labels reuse the existing visualization.kpi.kpi_selection translations
// for the matching table-mode KPI variants (cumulative distance, velocity_max, cumulative work).
// Only the base KPI names are shown for aggregated export (same as table view in TabWindowKPI).
// The cumulative_* variants are excluded because they duplicate the base names for aggregated display.
const KPI_AGG_NAMES = new Set([
  "distance_covered",
  "velocity",
  "metabolic_power",
  "equivalent_distance",
  "centroid_distance",
]);
const KPI_AGG_TRANSLATION_KEY = {
  distance_covered: "running_distance_cumulative",
  velocity: "velocity_max",
  metabolic_power: "metabolic_work_cumulative",
  equivalent_distance: "equivalent_distance_cumulative",
  centroid_distance: "centroid_distance_max",
};
const kpiNameItemsAggregated = computed(() =>
  (visualizationStore.kpiNames || [])
    .filter((name) => KPI_AGG_NAMES.has(name))
    .map((name) => {
      const key = KPI_AGG_TRANSLATION_KEY[name];
      return {
        id: name,
        name: key ? t(`visualization.kpi.kpi_selection.${key}`, name) : name,
      };
    })
);

const isKpiTeamSelectAll = ref(false);
const toggleKpiTeamSelectAll = (parameter) => {
  if (!isKpiTeamSelectAll.value) {
    parameter.value = kpiTeams.value.map((team) => team.id);
  } else {
    parameter.value = [];
  }
  isKpiTeamSelectAll.value = !isKpiTeamSelectAll.value;
};

const isKpiNamesSelectAll = ref(false);
const toggleKpiNamesSelectAll = (parameter) => {
  if (!isKpiNamesSelectAll.value) {
    parameter.value = kpiNameItems.value.map((item) => item.id);
  } else {
    parameter.value = [];
  }
  isKpiNamesSelectAll.value = !isKpiNamesSelectAll.value;
};

const isKpiNamesAggregatedSelectAll = ref(false);
const toggleKpiNamesAggregatedSelectAll = (parameter) => {
  if (!isKpiNamesAggregatedSelectAll.value) {
    parameter.value = kpiNameItemsAggregated.value.map((item) => item.id);
  } else {
    parameter.value = [];
  }
  isKpiNamesAggregatedSelectAll.value = !isKpiNamesAggregatedSelectAll.value;
};

const isKpiAttributeSelectAll = ref(false);
const toggleKpiAttributeSelectAll = (parameter) => {
  if (!isKpiAttributeSelectAll.value) {
    parameter.value = exportStore.selectableKpiAttributes.map((a) => a.id);
  } else {
    parameter.value = [];
  }
  isKpiAttributeSelectAll.value = !isKpiAttributeSelectAll.value;
};

const calibrationAssets = computed(() => {
  return Object.values(calibrationAssetStore.calibrationAssetsList);
});

const trackingDatasets = computed(() => {
  return Object.values(positionDataStore.positionDataList);
});

const formatLocalDate = (dateString) => {
  if (!dateString) return "";
  let isoString = dateString.replace(" ", "T");
  if (!isoString.endsWith("Z")) {
    isoString += "Z";
  }
  const date = new Date(isoString);
  const isoDate = date.toISOString().slice(0, 10);
  const localTime = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${isoDate} ${localTime}`;
};

const bytetrackRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .filter((e) => e.type === "bytetrack" && e.status === "DONE")
    .map((e) => ({
      id: e.id,
      name: formatLocalDate(e.date),
    }));
});

onMounted(() => {
  calibrationAssetStore.loadCalibrationAssetsList();
  positionDataStore.loadPositionDataList();
});
</script>

<style scoped>
.checkbox-label-spacing .v-label {
  margin-left: 6px;
}
</style>
