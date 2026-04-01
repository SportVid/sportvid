<template>
  <div>
    <template v-for="parameter in parameters.filter(p => !p.hidden)">
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

      <div v-if="parameter.field == 'select_calibration'" :key="parameter.name">
        <div class="d-flex ga-2 mb-6">
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
        :items="trackingDatasets"
        :label="parameter.text"
        :hint="parameter.hint"
        item-title="name"
        item-value="id"
        v-if="parameter.field == 'select_tracking_data'"
        :key="parameter.name"
        persistent-hint
        variant="underlined"
        class="mb-4"
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
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useTimelineStore } from "../stores/timeline";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useTopViewStore } from "@/stores/top_view";
import ModalCalibrationAssetSelect from "@/components/calibration-asset/ModalCalibrationAssetSelect.vue";
import { useExportStore } from "@/stores/export";
import { usePositionDataStore } from "@/stores/position_data";
import { useVisualizationStore } from "@/stores/visualization";

const timelineStore = useTimelineStore();
const calibrationAssetStore = useCalibrationAssetStore();
const topViewStore = useTopViewStore();
const exportStore = useExportStore();
const positionDataStore = usePositionDataStore();
const visualizationStore = useVisualizationStore();

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
  const teams = new Set(
    topViewStore.precomputedPlayerList.map((p) => p.teamId)
  );

  if (teams.size === 0) {
    return;
  }

  const sortedTeams = [...teams].sort((a, b) => {
    if (a === 1) return -1;
    if (b === 1) return 1;
    return a - b;
  });

  const meta = topViewStore.metaDataTopView;
  const teamItems = sortedTeams.map((team_id) => {
    const teamName = meta?.team_ids?.[team_id]?.name;
    return { id: team_id, name: teamName };
  });

  return teamItems;
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
  const kpiData = visualizationStore.kpiData;
  if (!kpiData || Object.keys(kpiData).length === 0) return [];

  const teams = new Set(
    Object.values(kpiData)
      .flat()
      .map((entry) => entry[1])
  );
  const sortedTeams = [...teams].sort((a, b) => a - b);
  const meta = topViewStore.metaDataTopView;
  return sortedTeams.map((team_id) => ({
    id: team_id,
    name: meta?.team_ids?.[team_id]?.name ?? String(team_id),
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
const KPI_AGG_TRANSLATION_KEY = {
  distance_covered: "running_distance_cumulative",
  velocity: "velocity_max",
  metabolic_power: "metabolic_work_cumulative",
};
const kpiNameItemsAggregated = computed(() =>
  (visualizationStore.kpiNames || []).map((name) => {
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
