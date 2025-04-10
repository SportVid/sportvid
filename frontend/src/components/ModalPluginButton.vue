<template>
  <div>
    <v-btn @click="showModalPlugin = true">
      <v-icon color="primary">mdi-plus</v-icon>
      {{ $t("app_bar.plugin_menu") }}
    </v-btn>

    <ModalPlugin v-model="showModalPlugin" :videoIds="[videoId]" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import ModalPlugin from "@/components/ModalPlugin.vue";

const playerStore = usePlayerStore();

const showModalPlugin = ref(false);

const videoId = computed(() => playerStore.videoId);
</script>
