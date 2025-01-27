import { createRouter, createWebHistory } from 'vue-router';
import Home from '@/views/Home.vue';
import VideoAnalysis from '@/views/Analysis.vue';

const routes = [
    {
        path: '/',
        name: 'Home',
        component: Home
    },
    {
        path: '/video-analysis',
        name: 'VideoAnalysis',
        component: VideoAnalysis
    }
  ];

const router = createRouter({
    history: createWebHistory(process.env.BASE_URL),
    routes,
});

export default router;