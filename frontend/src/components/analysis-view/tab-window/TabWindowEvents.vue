<template>
  <v-card class="d-flex flex-column flex-nowrap px-2 mb-1" elevation="0">
    <v-data-table :headers="headers" :items="items" class="elevation-2 my-2" />
  </v-card>
</template>

<script setup>
import { ref } from "vue";

const headers = [
  { title: "Timestamp", value: "timestamp" },
  { title: "Event", value: "event" },
  { title: "ID", value: "id" },
  { title: "Team", value: "team_id" },
];

const items = ref([
  { timestamp: "00:01", event: "Goal", id: "Player 1", team_id: "Team A" },
  { timestamp: "00:03", event: "Foul", id: "Player 2", team_id: "Team B" },
  { timestamp: "00:05", event: "Substitution", id: "Player 3", team_id: "Team A" },
]);
</script>
