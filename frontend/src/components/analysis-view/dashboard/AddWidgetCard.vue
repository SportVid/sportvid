<template>
  <v-card
    elevation="0"
    variant="tonal"
    class="add-widget-card fill-height d-flex align-center justify-center"
  >
    <v-menu v-if="options.length">
      <template #activator="{ props: menuProps }">
        <v-btn v-bind="menuProps" icon size="large" variant="text">
          <v-icon size="32">mdi-plus</v-icon>
        </v-btn>
      </template>
      <v-list density="compact">
        <v-list-item v-for="option in options" :key="option.id" @click="select(option.id)">
          <v-list-item-title>{{ $t(option.labelKey) }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <v-icon v-else size="32" class="text-medium-emphasis">mdi-plus</v-icon>
  </v-card>
</template>

<script setup>
import { computed } from "vue";
import { useDashboardLayoutStore } from "@/stores/dashboard_layout";
import { dashboardWidgets } from "@/config/dashboardWidgets";

const props = defineProps({
  rowIdx: { type: Number, required: true },
});

const dashboardStore = useDashboardLayoutStore();

const options = computed(() =>
  dashboardStore.availableWidgetIds.map((id) => ({
    id,
    labelKey: dashboardWidgets[id].labelKey,
  }))
);

function select(id) {
  if (dashboardWidgets[id].solo) {
    dashboardStore.addSolo(props.rowIdx, id);
  } else {
    dashboardStore.addGroupWidget(props.rowIdx, id);
  }
}
</script>

<style scoped>
.add-widget-card {
  min-height: 120px;
  border: 2px dashed rgba(var(--v-theme-on-surface), 0.3);
}
</style>
