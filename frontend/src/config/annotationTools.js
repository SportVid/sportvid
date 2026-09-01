import BboxAnnotationTool from "@/components/annotation-tool/BboxAnnotationTool.vue";
import BboxIdentityPanel from "@/components/annotation-tool/BboxIdentityPanel.vue";
import EventEditPanel from "@/components/annotation-tool/EventEditPanel.vue";
import AnnotationToolPreview from "@/components/annotation-tool/AnnotationToolPreview.vue";

// Central registry of the annotation tools offered in AnnotationView, keyed by tool id.
// Same shape and purpose as dashboardWidgets.js: the view looks a tool up here and renders it,
// so adding one means adding an entry plus its i18n labels -- the view itself never changes.
//
// Key order is menu order: calibration first, then the trackers, event data last.
//
// Per entry:
//   component     overlay drawn on top of the still frame (null = the tool draws nothing)
//   panel         right-hand properties panel (null = no panel for this tool)
//   pluginTypes   which plugin runs this tool can correct -- what maps a finished run onto
//                 the tool that knows how to review it
//   strip         what sits under the stage: "frames" (sampled still frames) or "timeline"
//                 (the full event timeline, same component the Events card uses)
//   playback      true = the video runs in this tool rather than being parked on a still
//                 frame, so the view mirrors playerStore onto its <video> and shows the
//                 transport bar. A frame-by-frame tool wants the opposite: a fixed frame that
//                 nothing moves out from under the boxes being dragged.
//   panelWide     the properties panel needs more than the default 280px (the event tool
//                 carries its event list in the same column)
//   actions       everything this tool can do, in toolbar order. Purely declarative: the view
//                 binds state and handlers to the ids (see actionState there) and shows the
//                 whole set for the active tool, disabling what isn't possible right now --
//                 so which corrections a tool offers is readable here, not buried in markup.
//   ready         false = selectable and visible, but nothing can be edited yet. Kept in the
//                 registry rather than hidden so the shape of the finished feature is visible
//                 while only the bbox path actually has data behind it.
export const annotationTools = {
  calibration: {
    component: AnnotationToolPreview,
    panel: null,
    labelKey: "annotation_tool.tools.calibration.name",
    descriptionKey: "annotation_tool.tools.calibration.description",
    icon: "mdi-vector-polyline",
    pluginTypes: ["calibration_static_dlt"],
    strip: "frames",
    actions: [
      {
        id: "move_marker",
        icon: "mdi-vector-point",
        labelKey: "annotation_tool.actions.move_marker",
      },
      {
        id: "add_marker",
        icon: "mdi-map-marker-plus-outline",
        labelKey: "annotation_tool.actions.add_marker",
      },
      {
        id: "fix_segment",
        icon: "mdi-vector-polyline-edit",
        labelKey: "annotation_tool.actions.fix_segment",
      },
    ],
    ready: false,
  },
  bbox: {
    component: BboxAnnotationTool,
    panel: BboxIdentityPanel,
    labelKey: "annotation_tool.tools.bbox.name",
    descriptionKey: "annotation_tool.tools.bbox.description",
    icon: "mdi-vector-square",
    pluginTypes: ["object_tracker"],
    strip: "frames",
    actions: [
      { id: "select", icon: "mdi-cursor-default-outline", labelKey: "annotation_tool.mode.select" },
      { id: "draw", icon: "mdi-shape-rectangle-plus", labelKey: "annotation_tool.mode.draw" },
      // Both destructive, so they sit together below the separator -- and both red, see
      // AnnotationView's bboxActionState.
      {
        id: "delete",
        icon: "mdi-delete-outline",
        labelKey: "annotation_tool.mode.delete",
        separated: true,
      },
      {
        id: "discard",
        icon: "mdi-undo-variant",
        labelKey: "annotation_tool.discard_frame",
      },
    ],
    ready: true,
  },
  events: {
    // Nothing to draw on the picture: an event has no geometry, only a moment, and where that
    // moment sits is what the timeline below the stage shows. A caption over the video would
    // only repeat the panel next to it.
    component: null,
    panel: EventEditPanel,
    panelWide: true,
    playback: true,
    labelKey: "annotation_tool.tools.events.name",
    descriptionKey: "annotation_tool.tools.events.description",
    icon: "mdi-flag-variant-outline",
    // No plugin produces event data yet (see events.js -- the sets are client-side dummies),
    // so there is nothing to map a run onto here.
    pluginTypes: [],
    strip: "timeline",
    // Only what has no home anywhere else. Retyping an event, reassigning its player and
    // moving it in time are all properties of one selected event, so they live in the panel
    // (and on the timeline, which is where a move is actually dragged) rather than as toolbar
    // buttons that would only put the panel's own controls in a second place.
    actions: [
      {
        id: "add_event",
        icon: "mdi-flag-plus-outline",
        labelKey: "annotation_tool.actions.add_event",
      },
      {
        id: "delete_event",
        icon: "mdi-flag-remove-outline",
        labelKey: "annotation_tool.actions.delete_event",
        separated: true,
      },
      {
        id: "discard_events",
        icon: "mdi-undo-variant",
        labelKey: "annotation_tool.actions.discard_events",
      },
    ],
    ready: true,
  },
};

export const annotationToolIds = Object.keys(annotationTools);

// Which tool knows how to correct a given plugin run type. Nothing outside AnnotationView
// routes by plugin type today (the target menu asks the tools directly), but `pluginTypes` is
// what makes that mapping possible from anywhere.
export function toolIdForPluginType(type) {
  return annotationToolIds.find((id) => annotationTools[id].pluginTypes.includes(type)) ?? null;
}
