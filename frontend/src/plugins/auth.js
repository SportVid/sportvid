import { useUserStore } from '@/stores/user';

export default {
  install(app) {
    const userStore = useUserStore();
    
    app.config.globalProperties.$auth = {
      async initializeAuth() {
        await userStore.getCSRFToken();
        await userStore.getUserData();
      },
    };
  }
};