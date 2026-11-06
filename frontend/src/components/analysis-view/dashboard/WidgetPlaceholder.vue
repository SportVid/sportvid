<template>
  <div class="widget-placeholder fill-height d-flex flex-column align-center justify-center">
    <v-icon size="68" class="widget-placeholder-icon">{{ icon }}</v-icon>
    <div class="widget-placeholder-label">{{ $t(labelKey) }}</div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { dashboardWidgets } from "@/config/dashboardWidgets";

const props = defineProps({
  widgetId: { type: String, required: true },
});

const icon = computed(() => dashboardWidgets[props.widgetId]?.icon ?? "mdi-image-outline");
const labelKey = computed(() => dashboardWidgets[props.widgetId]?.labelKey ?? props.widgetId);
</script>

<style scoped>
.widget-placeholder {
  width: 100%;
  height: 100%;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.widget-placeholder-icon {
  opacity: 0.6;
}

.widget-placeholder-label {
  margin-top: 12px;
  font-size: 1.3rem;
  font-weight: 500;
}
</style>
