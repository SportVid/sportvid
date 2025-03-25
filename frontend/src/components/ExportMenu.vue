<template>
  <div>
    <v-menu min-width="175" offset-y bottom left>
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" @click="showModalExport = true">
          <v-icon color="primary">mdi-swap-vertical-bold</v-icon>
          {{ $t("app_bar.export_menu") }}
        </v-btn>
      </template>
    </v-menu>

    <ModalExport v-model="showModalExport"> </ModalExport>
  </div>
</template>

<script setup>
import { ref } from "vue";
import ModalExport from "@/components/ModalExport.vue";

const showModalExport = ref(false);
</script>

<style>
.v-menu__content .v-btn:not(.accent) {
  text-transform: capitalize;
  justify-content: left;
}

.v-btn:not(.v-btn--round).v-size--large {
  height: 48px;
}
</style>
