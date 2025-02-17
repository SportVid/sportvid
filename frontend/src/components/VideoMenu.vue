<template>
  <div>
    <v-menu min-width="175" offset-y bottom left>
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" @click="showModalExport = true">
          <v-icon color="primary">mdi-swap-vertical-bold</v-icon>
          Export
        </v-btn>
      </template>
    </v-menu>

    <ModalExport v-model="showModalExport"> </ModalExport>
  </div>
</template>

<script>
import { ref, computed } from "vue";
import { useUserStore } from "@/stores/user";
import { usePlayerStore } from "@/stores/player";
import ModalExport from "@/components/ModalExport.vue";

export default {
  components: {
    ModalExport,
  },
  setup() {
    const userStore = useUserStore();
    const playerStore = usePlayerStore();

    const showModalExport = ref(false);

    const videoId = computed(() => playerStore.videoId);
    const loggedIn = computed(() => userStore.loggedIn);

    return {
      showModalExport,
      videoId,
      loggedIn,
    };
  },
};
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
