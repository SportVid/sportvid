<template>
  <div class="position-data-menu-root" data-tour="position-data-menu">
    <!-- Large, very faint watermark behind the whole box (buttons included) -- purely so the
         card doesn't look bare while empty, same icon as the edit-mode WidgetPlaceholder uses
         for this widget. pointer-events: none keeps it from ever intercepting clicks even
         where it overlaps the buttons. -->
    <div v-if="icon" class="position-data-menu-watermark">
      <v-icon :size="400">{{ icon }}</v-icon>
    </div>

    <v-col class="position-data-menu-col" style="position: relative">
      <!-- Shown while this card has nothing else to display (see the various cards' own
           empty-state branches) -- with no other content around it here, this is the only
           way to tell which card an empty box on the dashboard actually belongs to. Pinned to
           the top -- only the button block below (.position-data-menu-body) is vertically
           centered. -->
      <v-row v-if="title" class="position-data-menu-title mt-2" style="justify-content: center">
        {{ title }}
      </v-row>

      <div class="position-data-menu-body">
        <template v-if="canWrite">
          <v-row style="justify-content: center" class="mt-8">
            <v-col cols="10">
              <v-sheet border rounded class="pa-4 bg-transparent">
                <v-row
                  class="text-caption text-grey text-uppercase mt-4 mb-2"
                  style="justify-content: center"
                >
                  {{ $t("position_data.generate.cv_heading") }}
                </v-row>
                <!-- Complex mode: full choice of individual plugins, each opening its own
                     parameter modal. -->
                <v-row
                  v-if="userStore.experienceMode !== 'simple'"
                  style="justify-content: center"
                  class="mt-1 ga-4"
                >
                  <v-btn
                    data-tour="posdata-generate-bytetrack"
                    @click="showObjectTrackerModal = true"
                  >
                    {{ $t("position_data.generate.object_tracker") }}
                  </v-btn>

                  <v-btn data-tour="posdata-generate-dlt" @click="showDltModal = true">
                    {{ $t("position_data.generate.dlt") }}
                  </v-btn>

                  <!-- Optional refinement on top of an existing (player-)Object Tracker run --
                       both open their own run picker inside the modal, so they stay usable even
                       before/without one, same as Object Tracker/DLT above don't gate on
                       each other either. -->
                  <v-btn
                    data-tour="posdata-generate-team-assignment"
                    @click="showTeamAssignmentModal = true"
                  >
                    {{ $t("position_data.generate.team_assignment") }}
                  </v-btn>

                  <v-btn
                    data-tour="posdata-generate-re-identification"
                    @click="showReIdentificationModal = true"
                  >
                    {{ $t("position_data.generate.re_identification") }}
                  </v-btn>

                  <!-- Only relevant when this box is the KPI card's empty state -- KPI
                       computation has its own params (own tracking_data/calibration pickers,
                       see kpiComputationParams), so it doesn't need position data to already be
                       selected/loaded and can be triggered right from here too. -->
                  <v-btn
                    v-if="showKpiButton"
                    data-tour="posdata-generate-kpi-computation"
                    @click="showKpiComputationModal = true"
                  >
                    {{ $t("visualization.kpi.compute_kpis") }}
                  </v-btn>
                </v-row>

                <!-- Simple mode: one combined "Create Position Data" flow (calibration asset +
                     player/ball tracking + team assignment/re-id as checkboxes, sequenced and
                     run together, see ModalPositionDataCreate.vue) instead of picking each
                     plugin separately. KPI computation still gets its own button/modal (same
                     one Complex mode uses above) since it already bundles its own asset
                     pickers and doesn't depend on anything else in this flow. -->
                <v-row v-else style="justify-content: center" class="mt-1 ga-4">
                  <v-btn
                    data-tour="posdata-generate-create"
                    @click="showPositionDataCreateModal = true"
                  >
                    {{ $t("position_data.generate.create") }}
                  </v-btn>

                  <v-btn
                    v-if="showKpiButton"
                    data-tour="posdata-generate-kpi-computation"
                    @click="showKpiComputationModal = true"
                  >
                    {{ $t("visualization.kpi.compute_kpis") }}
                  </v-btn>
                </v-row>

                <v-row style="justify-content: center; align-items: center" class="mt-4 mb-n2">
                  <v-col cols="4" class="d-flex align-center">
                    <v-divider />
                  </v-col>
                  <v-col cols="auto" class="text-grey px-2">{{
                    $t("position_data.generate.or")
                  }}</v-col>
                  <v-col cols="4" class="d-flex align-center">
                    <v-divider />
                  </v-col>
                </v-row>

                <v-row
                  class="text-caption text-grey text-uppercase mb-2"
                  style="justify-content: center"
                >
                  {{ $t("position_data.generate.upload_heading") }}
                </v-row>
                <v-row style="justify-content: center" class="mt-1 mb-4">
                  <v-btn
                    data-tour="posdata-manual-upload-open"
                    @click="showModalPositionDataUpload = true"
                    >{{ $t("position_data.display_settings.position_data.upload") }}</v-btn
                  >
                </v-row>
              </v-sheet>
            </v-col>
          </v-row>

          <ModalPluginRun
            v-if="showObjectTrackerModal"
            v-model="showObjectTrackerModal"
            plugin="object_tracker"
            :name="$t('modal.plugin.object_tracker.plugin_name')"
            :description="$t('modal.plugin.object_tracker.plugin_description')"
            :paramsFactory="objectTrackerParams"
            :videoId="playerStore.videoId"
            runButtonDataTour="posdata-bytetrack-run"
          />
          <ModalPluginRun
            v-if="showDltModal"
            v-model="showDltModal"
            plugin="calibration_static_dlt"
            :name="$t('modal.plugin.calibration_static_dlt.plugin_name')"
            :description="$t('modal.plugin.calibration_static_dlt.plugin_description')"
            :paramsFactory="dltParams"
            :videoId="playerStore.videoId"
            runButtonDataTour="posdata-dlt-apply"
          />
          <ModalPluginRun
            v-if="showTeamAssignmentModal"
            v-model="showTeamAssignmentModal"
            plugin="team_clustering"
            :name="$t('modal.plugin.team_clustering.plugin_name')"
            :description="$t('modal.plugin.team_clustering.plugin_description')"
            :paramsFactory="teamClusteringParams"
            :videoId="playerStore.videoId"
            runButtonDataTour="posdata-team-assignment-run"
          />
          <ModalPluginRun
            v-if="showReIdentificationModal"
            v-model="showReIdentificationModal"
            plugin="osnet_reid"
            :name="$t('modal.plugin.osnet_reid.plugin_name')"
            :description="$t('modal.plugin.osnet_reid.plugin_description')"
            :paramsFactory="osnetReidParams"
            :videoId="playerStore.videoId"
            runButtonDataTour="posdata-re-identification-run"
          />
          <ModalPluginRun
            v-if="showKpiComputationModal"
            v-model="showKpiComputationModal"
            plugin="kpi_computation"
            :name="$t('modal.plugin.kpi_computation.plugin_name')"
            :description="$t('modal.plugin.kpi_computation.plugin_description')"
            :paramsFactory="kpiComputationParams"
            :videoId="playerStore.videoId"
            runButtonDataTour="posdata-kpi-computation-run"
          />
          <ModalPositionDataCreate
            v-if="showPositionDataCreateModal"
            v-model="showPositionDataCreateModal"
            :videoId="playerStore.videoId"
          />
        </template>

        <v-row style="justify-content: center" :class="showKpiButton ? 'mt-8 mb-4' : 'mt-10 mb-6'">
          <v-menu v-if="selectDisabled" location="top center" open-on-hover>
            <template #activator="{ props: menuProps }">
              <!-- Disabled v-btn elements don't fire pointer events, so the hover activator has
                   to sit on a plain (non-disabled) wrapper around it instead. -->
              <span v-bind="menuProps">
                <v-btn disabled>{{
                  $t("position_data.display_settings.position_data.select")
                }}</v-btn>
              </span>
            </template>
            <v-sheet class="pa-3 select-disabled-hint" align="center" style="max-width: 350px">
              {{
                !hasAvailablePositionData
                  ? $t("position_data.not_selected")
                  : $t("position_data.kpi_not_selected")
              }}
              {{ $t("position_data.select_disabled_hint_prefix")
              }}<a href="#" @click.prevent="openStatusOverview">{{
                $t("position_data.status_overview_link")
              }}</a
              >{{ $t("position_data.select_disabled_hint_suffix") }}
            </v-sheet>
          </v-menu>
          <v-btn v-else :disabled="selectDisabled" @click="showModalPositionDataSelect = true">
            {{ $t("position_data.display_settings.position_data.select") }}
          </v-btn>
          <ModalPositionDataSelect
            v-if="showModalPositionDataSelect"
            v-model="showModalPositionDataSelect"
          />
        </v-row>

        <ModalPositionDataUpload
          v-if="showModalPositionDataUpload"
          v-model="showModalPositionDataUpload"
        />
      </div>
    </v-col>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import { usePluginRunStore } from "@/stores/plugin_run";
import {
  objectTrackerParams,
  dltParams,
  teamClusteringParams,
  osnetReidParams,
  kpiComputationParams,
} from "@/composables/usePluginParams";
import { usePositionDataStatus } from "@/composables/usePositionDataStatus";
import ModalPluginRun from "@/components/app/app-bar/ModalPluginRun.vue";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";
import ModalPositionDataCreate from "@/components/position-data/ModalPositionDataCreate.vue";

const props = defineProps({
  // Shown as a heading while this box is up -- lets the user tell which (otherwise
  // content-less) card they're looking at. Omit for usages that don't need it.
  title: { type: String, default: null },
  // mdi icon name, shown as a large faint watermark behind the whole box -- same icon as this
  // widget's entry in dashboardWidgets.js (see WidgetPlaceholder, the edit-mode equivalent).
  icon: { type: String, default: null },
  // Adds a 5th "Compute KPIs" button alongside Object Tracker/DLT/Team Assignment/Re-ID --
  // only the KPI card needs this, TopView/Heatmap only ever need generic position data.
  showKpiButton: { type: Boolean, default: false },
});

const playerStore = usePlayerStore();
const userStore = useUserStore();
const pluginRunStore = usePluginRunStore();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const showModalPositionDataUpload = ref(false);
const showModalPositionDataSelect = ref(false);
const showObjectTrackerModal = ref(false);
const showDltModal = ref(false);
const showTeamAssignmentModal = ref(false);
const showReIdentificationModal = ref(false);
const showKpiComputationModal = ref(false);
const showPositionDataCreateModal = ref(false);

const { posdataAvailable, kpiState } = usePositionDataStatus();
const hasAvailablePositionData = posdataAvailable;

// KPI needs a second, separate gate: even once position data exists, the Select button stays
// disabled until at least one kpi_computation run has also finished -- otherwise there'd be
// nothing worth picking in ModalPositionDataSelect for the KPI card specifically. Only applies
// when this box is the KPI card's (showKpiButton), TopView/Heatmap don't care about KPI data.
const hasAvailableKpiData = computed(() => kpiState.value === "done");
const selectDisabled = computed(() => {
  if (!hasAvailablePositionData.value) return true;
  if (props.showKpiButton && !hasAvailableKpiData.value) return true;
  return false;
});

// Detailed per-step status (player tracking/DLT/KPI, running vs. done vs. error) lives in
// ModalStatus (the app-bar's status overview) -- rather than duplicating that breakdown here,
// the disabled Select button's hover popup links straight to it. See
// pluginRunStore.openStatusModal / AppBar.vue's watcher for the remote-open mechanism.
const openStatusOverview = () => {
  pluginRunStore.openStatusModal = true;
};
</script>

<style scoped>
/* Flex column so .position-data-menu-col (below) can grow to fill this box's whole height
   (min-height: 60vh, or taller once the card gets more room). */
.position-data-menu-root {
  min-height: 60vh;
  position: relative;
  display: flex;
  flex-direction: column;
}

/* v-col already flex-grows to fill the parent by Vuetify default -- that's what makes it fill
   .position-data-menu-root's height. Making it a flex column of its own lets the title
   (natural size, pinned to the top) and .position-data-menu-body (below) be laid out
   independently, instead of naively centering title+body as one block. */
.position-data-menu-col {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* The actual button block -- grows to fill whatever's left under the title and centers its own
   content in that space. Without this, on taller/larger screens the card grows well past the
   60vh floor but the buttons just stayed pinned to the top via their own mt-* offsets, leaving
   a large empty gap below. */
.position-data-menu-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.position-data-menu-watermark {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30px;
  opacity: 0.02;
  pointer-events: none;
  overflow: hidden;
}

/* Matches VideoPlayer's .video-title / TopView's .matchup-title font metrics -- Vuetify's
   text-h6 utility class looked taller here because its line-height (2rem) is considerably
   more generous than either of those hand-tuned headers use. */
.position-data-menu-title {
  font-size: 1.25rem;
  font-weight: 500;
}

.select-disabled-hint a {
  color: rgb(var(--v-theme-primary));
  text-decoration: underline;
}
</style>
