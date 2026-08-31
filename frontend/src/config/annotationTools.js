import BboxAnnotationTool from "@/components/annotation-tool/BboxAnnotationTool.vue";

// Central registry of the annotation tools offered in AnnotationToolView, keyed by tool id.
// Same shape and purpose as dashboardWidgets.js: the view looks a tool up here and renders it,
// so adding one (calibration point correction, event timing, ...) means adding an entry plus
// its i18n label -- the view itself never changes.
//
// `pluginTypes` says which plugin runs a tool can correct. It is what maps a finished run in
// the status overview onto the tool that knows how to review it.
export const annotationTools = {
  bbox: {
    component: BboxAnnotationTool,
    labelKey: "annotation_tool.tools.bbox.name",
    descriptionKey: "annotation_tool.tools.bbox.description",
    icon: "mdi-vector-square",
    pluginTypes: ["object_tracker", "bytetrack"],
  },
};

export const annotationToolIds = Object.keys(annotationTools);

// Every plugin type that any tool can review -- used to decide whether a finished run in
// ModalStatus gets a "correct this" action.
export const annotatablePluginTypes = annotationToolIds.flatMap(
  (id) => annotationTools[id].pluginTypes
);

export function toolIdForPluginType(type) {
  return annotationToolIds.find((id) => annotationTools[id].pluginTypes.includes(type)) ?? null;
}
