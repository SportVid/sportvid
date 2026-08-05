import VideoPlayer from "@/components/analysis-view/cards/VideoPlayer.vue";
import TopView from "@/components/analysis-view/cards/TopView.vue";
import TabWindowTimeline from "@/components/analysis-view/cards/tab-window/TabWindowTimeline.vue";
import TabWindowEvents from "@/components/analysis-view/cards/tab-window/TabWindowEvents.vue";
import TabWindowHeatmap from "@/components/analysis-view/cards/tab-window/TabWindowHeatmap.vue";
import TabWindowKPI from "@/components/analysis-view/cards/tab-window/TabWindowKPI.vue";

// Central registry of all dashboard widgets. Replaces the old
// getVisualizationTabComponent switch — the DashboardGrid/DashboardCell
// components look widgets up here by id.
export const dashboardWidgets = {
  video: {
    component: VideoPlayer,
    labelKey: "analysis_view.dashboard.widgets.video",
    solo: true,
    permanent: true,
    taggable: false,
    icon: "mdi-video-outline",
  },
  topview: {
    component: TopView,
    labelKey: "analysis_view.dashboard.widgets.topview",
    solo: true,
    permanent: false,
    taggable: false,
    icon: "mdi-soccer-field",
  },
  timeline: {
    component: TabWindowTimeline,
    labelKey: "analysis_view.visualization_tabs.timeline",
    solo: false,
    permanent: false,
    taggable: true,
    icon: "mdi-chart-timeline-variant",
  },
  events: {
    component: TabWindowEvents,
    labelKey: "analysis_view.visualization_tabs.events",
    solo: false,
    permanent: false,
    taggable: true,
    icon: "mdi-flag-variant-outline",
  },
  heatmap: {
    component: TabWindowHeatmap,
    labelKey: "analysis_view.visualization_tabs.heatmap",
    solo: false,
    permanent: false,
    taggable: true,
    icon: "mdi-fire",
  },
  kpi: {
    component: TabWindowKPI,
    labelKey: "analysis_view.visualization_tabs.kpi",
    solo: false,
    permanent: false,
    taggable: true,
    icon: "mdi-speedometer",
  },
};

export const dashboardWidgetIds = Object.keys(dashboardWidgets);

export function isSoloWidget(id) {
  return !!dashboardWidgets[id]?.solo;
}

export function isTaggableWidget(id) {
  return !!dashboardWidgets[id]?.taggable;
}
