import { onBeforeRouteLeave } from "vue-router";
import { usePositionDataStore } from "@/stores/position_data";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useTopViewStore } from "@/stores/top_view";
import { useEventsStore } from "@/stores/events";

// Routes that all work on the same video's analysis state. Position data, the calibration
// asset and the derived top-view data all live in app-level pinia stores, so they survive a
// route change on their own -- they only ever disappear because a view explicitly tears them
// down on unmount. Navigating between the routes listed here must therefore NOT tear them
// down: reloading them means re-running transformBBoxToPositionDataTopView plus the ball /
// team-clustering / reid merges plus the KPI load (see position_data.js's _restoreTracker),
// which is the single most expensive thing in the app.
export const ANALYSIS_SCOPED_ROUTES = ["AnalysisView", "AnnotationToolView"];

// The teardown itself, formerly inline in AnalysisView.vue's onBeforeUnmount.
export function resetAnalysisScope() {
  const positionDataStore = usePositionDataStore();
  const calibrationAssetStore = useCalibrationAssetStore();
  const topViewStore = useTopViewStore();
  const eventsStore = useEventsStore();

  // Also clears the persisted tracker-run ids (bboxPluginRunId/bboxBallPluginRunId,
  // teamClusteringRunId/reidRunId) -- otherwise they'd survive into a different video's
  // AnalysisView and restoreFromCache (position_data.js) could try to restore this video's
  // tracker run against that one.
  positionDataStore.resetPositionData();
  calibrationAssetStore.resetCalibrationAsset();
  topViewStore.gridLongitudinal = 0;
  topViewStore.gridTransverse = 0;
  topViewStore.showSportZones = false;
  // Event data sets (see EventDataMenu.vue) are only ever uploaded/generated per video, not
  // a reusable global list -- carrying them into the next video (persisted, see events.js)
  // would show that other video's dummy/uploaded events tagged onto this one instead of a
  // clean "no event data yet" state.
  eventsStore.resetEventData();
}

// Call from every view listed in ANALYSIS_SCOPED_ROUTES. Keeps the analysis state alive while
// the user moves between those views for the *same* video, and tears it down otherwise --
// including a jump straight from one video to another, where the ids differ but both route
// names are in scope.
export function useAnalysisScopeCleanup() {
  onBeforeRouteLeave((to, from) => {
    const staysInScope =
      ANALYSIS_SCOPED_ROUTES.includes(to.name) && to.params.id === from.params.id;
    if (!staysInScope) {
      resetAnalysisScope();
    }
  });
}
