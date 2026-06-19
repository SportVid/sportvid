import { createApp } from "vue";
import App from "./App.vue";
import { vuetify } from "@/plugins/vuetify";
import { i18n } from "@/plugins/i18n";
import auth from "@/plugins/auth";
import "shepherd.js/dist/css/shepherd.css";
import "@/styles/custom.css";

import { createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import router from "@/router";
import { useUserStore } from "@/stores/user";

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

async function bootstrap() {
  const app = createApp(App);

  app.use(vuetify);
  app.use(pinia);
  app.use(router);
  app.use(i18n);
  app.use(auth);

  const userStore = useUserStore(pinia);
  await userStore.getCSRFToken();
  await userStore.getUserData();

  app.mount("#app");
}
bootstrap();

// const app = createApp(App);

// app.use(vuetify);
// app.use(pinia);
// app.use(router);
// app.use(i18n);
// app.use(auth);

// const userStore = useUserStore(pinia);
// await userStore.getCSRFToken();
// await userStore.getUserData();

// app.mixin({
//   async created() {
//     const userStore = useUserStore();
//     await userStore.getCSRFToken();
//     await userStore.getUserData();
//   },
// });

// TODO: old client authentication state exists before backend confirms the session.

// app.mount("#app");