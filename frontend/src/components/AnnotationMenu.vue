<template>
  <div>
    <v-menu min-width="175" offset-y bottom left>
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" @click="showModalShortcut = true">
          <v-icon color="primary">mdi-label-multiple-outline</v-icon>
          Shortcuts
        </v-btn>
      </template>
    </v-menu>

    <ModalShortcut v-model="showModalShortcut" />
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import ModalShortcut from "@/components/ModalShortcut.vue";
import { useUserStore } from "@/stores/user";
import { usePlayerStore } from "@/stores/player";

export default {
  setup() {
    const showModalShortcut = ref(false);  
    const userStore = useUserStore();      
    const playerStore = usePlayerStore();  

    const videoId = computed(() => playerStore.videoId);  
    const loggedIn = computed(() => userStore.loggedIn);  

    return {
      showModalShortcut, 
      videoId,     
      loggedIn, 
    };
  },
  components: {
    ModalShortcut, 
  },
};
</script>

<style scoped>
.v-menu__content .v-btn:not(.accent) {
  text-transform: capitalize;
  justify-content: left;
}

.v-btn:not(.v-btn--round).v-size--large {
  height: 48px;
}
</style>
