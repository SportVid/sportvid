import { createApp } from 'vue';
import App from './App.vue';
import { vuetify } from '@/plugins/vuetify';
import { i18n } from '@/plugins/i18n';
import auth from '@/plugins/auth'
import '@/styles/custom.css';

import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
import router from '@/router';
import { useUserStore } from '@/stores/user';

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

const app = createApp(App);

app.mixin({
  async created() {
    const userStore = useUserStore();
    await userStore.getCSRFToken();
    await userStore.getUserData();
  },
});

app.use(vuetify);
app.use(pinia);
app.use(router);
app.use(i18n);
app.use(auth);

app.mount('#app');

