import { createRouter, createWebHistory } from "vue-router";
import { useUserStore } from "@/stores/user";
import VideoView from "@/views/VideoView.vue";
import AnalysisView from "@/views/AnalysisView.vue";
import TermsOfUseView from "@/views/TermsOfUseView.vue";
import GuidelinesView from "@/views/GuidelinesView.vue";
import ImpressumView from "@/views/ImpressumView.vue";
import AdminView from "@/views/AdminView.vue";

const routes = [
  {
    path: "/",
    name: "VideoView",
    component: VideoView,
  },
  {
    path: "/video-analysis/:id",
    name: "AnalysisView",
    component: AnalysisView,
  },
  {
    path: "/terms-of-use",
    name: "termsOfUseView",
    component: TermsOfUseView,
  },
  {
    path: "/guidelines",
    name: "GuidelinesView",
    component: GuidelinesView,
  },
  {
    path: "/impressum",
    name: "ImpressumView",
    component: ImpressumView,
  },
  {
    path: "/admin",
    name: "AdminView",
    component: AdminView,
    meta: {
      requiresAuth: true,
      requiresAdmin: true,
    },
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore();

  if (userStore.loggedIn && !userStore.role) {
    try {
      await userStore.getUserData();
    } catch (e) {
      console.error("Failed to fetch user data in router guard", e);
    }
  }

  if (to.meta.requiresAuth && !userStore.loggedIn) {
    return next({ name: "VideoView" });
  }

  if (to.meta.requiresAdmin && userStore.role !== "admin") {
    return next({ name: "VideoView" });
  }

  next();
});

export default router;
