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
import { ref, computed } from "vue";
import { useUserStore } from "@/stores/user";
import { usePlayerStore } from "@/stores/player";
import ModalExport from "@/components/ModalExport.vue";

const userStore = useUserStore();
const playerStore = usePlayerStore();

const showModalExport = ref(false);

const videoId = computed(() => playerStore.videoId);
const loggedIn = computed(() => userStore.loggedIn);
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
