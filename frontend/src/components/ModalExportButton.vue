<template>
  <div>
    <v-btn @click="showModalExport = true">
      <v-icon color="primary">mdi-swap-vertical-bold</v-icon>
      {{ $t("app_bar.export_menu") }}
    </v-btn>

    <ModalExport v-model="showModalExport" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import ModalExport from "@/components/ModalExport.vue";

const showModalExport = ref(false);
</script>
