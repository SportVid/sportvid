<template>
  <!-- Stand-in overlay for a tool that is selectable but has no editing path yet (registry
       entry with ready: false). Deliberately not a hidden/disabled tool: the point is that the
       finished feature's shape -- which corrections will be offered, and on what -- is visible
       now, while only the bbox tool actually has data behind it. -->
  <div class="tool-preview" data-annotation-layer>
    <div class="tool-preview-box">
      <v-icon size="34" class="mb-2">{{ icon }}</v-icon>
      <div class="tool-preview-title">{{ $t("annotation_tool.preview.title") }}</div>
      <div class="tool-preview-text">{{ $t(`annotation_tool.tools.${toolId}.description`) }}</div>
    </div>
  </div>
</template>

<script setup>
// toolId rather than the registry entry itself: config/annotationTools.js imports this
// component, so reaching back into it here would close an import cycle for no gain.
defineProps({
  toolId: { type: String, required: true },
  icon: { type: String, default: "mdi-toolbox-outline" },
  // Accepted (the view hands the same props to every tool overlay) but unused here.
  width: { type: Number, default: 0 },
  height: { type: Number, default: 0 },
  mode: { type: String, default: "select" },
});
</script>

<style scoped>
.tool-preview {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.tool-preview-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 380px;
  padding: 18px 22px;
  border-radius: 10px;
  border: 1px dashed rgba(255, 255, 255, 0.35);
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
}

.tool-preview-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 4px;
}

.tool-preview-text {
  font-size: 0.78rem;
  opacity: 0.85;
  line-height: 1.35;
}
</style>
