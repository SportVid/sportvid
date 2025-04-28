import { createRouter, createWebHistory } from "vue-router";
import VideoView from "@/views/VideoView.vue";
import AnalysisView from "@/views/AnalysisView.vue";
import TermsOfServiceView from "@/views/TermsOfServiceView.vue";

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
    path: "/terms-of-service",
    name: "TermsOfServiceView",
    component: TermsOfServiceView,
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

export default router;
