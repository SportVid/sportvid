<template>
  <v-app id="tibava">
    <v-app-bar>
      <img 
        :title="appName" 
        src="./assets/logo_tib_dshs.png" 
        height="50" 
        class="ml-2 mr-n2" 
      />
      <v-toolbar-title class="pr-12">SportVid</v-toolbar-title>

      <v-btn tile text to="/">
        <v-icon color="primary" class="mr-1">mdi-movie</v-icon>
        Videos
      </v-btn>

      <v-spacer></v-spacer>
      <v-btn class="mr-2" v-if="videoView">PluginMenu</v-btn>
      <v-btn class="mr-2" v-if="videoView">History</v-btn>
      <v-btn class="mr-2" v-if="videoView">AnnotationMenu</v-btn>
      <v-btn class="mr-4" v-if="videoView">VideoMenu</v-btn>
      <UserMenu />
    </v-app-bar>
    <router-view />
    <!-- <ModalError /> -->
  </v-app>
</template>

<script>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useUserStore } from "@/stores/user";
import { usePlayerStore } from "@/stores/player";
import { useErrorStore } from "@/stores/error";

import UserMenu from "@/components/UserMenu.vue";
// import VideoMenu from "@/components/VideoMenu.vue";
// import PluginMenu from "@/components/PluginMenu.vue";
// import AnnotationMenu from "@/components/AnnotationMenu.vue";
// import History from "./components/History.vue";
// import ModalError from "./components/ModalError.vue";

export default {
  components: {
    UserMenu,
    // VideoMenu,
    // PluginMenu,
    // AnnotationMenu,
    // History,
    // ModalError
  },
  setup() {
    const appName = process.env.VUE_APP_NAME;

    const route = useRoute();

    const userStore = useUserStore();
    const playerStore = usePlayerStore();
    const errorStore = useErrorStore();

    const loggedIn = computed(() => userStore.loggedIn);
    const videoView = computed(() => route.name === "VideoAnalysis");

    return {
      appName,
      loggedIn,
      videoView,
      userStore,
      playerStore,
      errorStore,
    };
  }
}
</script>

<style>
#tibava {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: left;
  color: #2c3e50;
}
</style>
