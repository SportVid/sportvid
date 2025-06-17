<template>
  <v-card class="d-flex flex-column flex-nowrap px-2 mb-1" elevation="0">
    <v-data-table :headers="headers" :items="eventItems" class="elevation-2 my-2" />
  </v-card>
</template>

<script setup>
import { ref } from "vue";

const headers = [
  { title: "Timestamp", value: "timestamp" },
  { title: "Aktion", value: "action" },
  { title: "Spieler", value: "player" },
  { title: "Mannschaft", value: "team" },
];

// Beispielhafte Events, die später durch ML-Plugins ergänzt oder ersetzt werden können
const eventItems = ref([
  { timestamp: "00:01", action: "Goal", player: "Player 1", team: "Team A" },
  { timestamp: "00:03", action: "Foul", player: "Player 2", team: "Team B" },
  { timestamp: "00:05", action: "Substitution", player: "Player 3", team: "Team A" },
]);
</script>
