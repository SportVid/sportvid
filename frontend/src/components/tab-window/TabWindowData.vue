<template>
  <v-card class="d-flex flex-column flex-nowrap px-2 mb-1" elevation="0">
    <v-menu location="bottom">
      <template #activator="{ props }">
        <v-btn v-bind="props">
          <v-icon left>mdi-cog</v-icon>
          {{ $t("data.options.title") }}
        </v-btn>
      </template>
      <v-list class="py-0" density="compact" width="220">
        <v-list-item class="menu-item" @click="visualizationStore.viewAggregatedFull">
          <v-list-item-title class="d-flex justify-space-between">
            {{ $t("data.options.aggregated_full") }}
            <tab-window-icon
              :class="{
                'text-disabled': !visualizationStore.showAggregatedFull,
                'text-red': visualizationStore.showAggregatedFull,
              }"
            >
              mdi-check
            </tab-window-icon>
          </v-list-item-title>
        </v-list-item>

        <v-list-item class="menu-item" @click="visualizationStore.viewAggregatedFirst">
          <v-list-item-title class="d-flex justify-space-between">
            {{ $t("data.options.aggregated_first") }}
            <tab-window-icon
              :class="{
                'text-disabled': !visualizationStore.showAggregatedFirst,
                'text-red': visualizationStore.showAggregatedFirst,
              }"
            >
              mdi-check
            </tab-window-icon>
          </v-list-item-title>
        </v-list-item>

        <v-list-item class="menu-item" @click="visualizationStore.viewAggregatedSecond">
          <v-list-item-title class="d-flex justify-space-between">
            {{ $t("data.options.aggregated_second") }}
            <tab-window-icon
              :class="{
                'text-disabled': !visualizationStore.showAggregatedSecond,
                'text-red': visualizationStore.showAggregatedSecond,
              }"
            >
              mdi-check
            </tab-window-icon>
          </v-list-item-title>
        </v-list-item>

        <v-list-item class="menu-item" @click="visualizationStore.viewProgress">
          <v-list-item-title class="d-flex justify-space-between">
            {{ $t("data.options.progress") }}
            <tab-window-icon
              :class="{
                'text-disabled': !visualizationStore.showProgress,
                'text-red': visualizationStore.showProgress,
              }"
            >
              mdi-check
            </tab-window-icon>
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <v-data-table :headers="headers" :items="items" class="elevation-2 my-2" />
  </v-card>
</template>

<script setup>
import { ref } from "vue";
import { useVisualizationStore } from "@/stores/visualization";

const visualizationStore = useVisualizationStore();

const headers = [
  { title: "ID", value: "id" },
  { title: "Mannschaft", value: "team" },
  { title: "Distance [m]", value: "distance" },
];

const items = ref([
  { id: "Player 1", team: "Team A", distance: 50 },
  { id: "Player 2", team: "Team A", distance: 60 },
  { id: "Player 3", team: "Team A", distance: 45 },
]);
</script>

<style scoped>
.menu-item {
  cursor: pointer;
}

.menu-item:hover {
  background-color: #f0f0f0;
}

.menu-item .v-list-item-title {
  font-size: 12px;
}
</style>
