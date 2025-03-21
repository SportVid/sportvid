<template>
  <v-main>
    <v-container v-if="userStore.loggedIn" class="py-8 px-6" fluid>
      <v-row justify="center">
        <v-col cols="10" md="3" class="d-flex flex-column align-center">
          <ModalVideoUpload />
        </v-col>
        <v-col cols="10" md="3" class="d-flex flex-column align-center">
          <v-btn
            class="mt-6"
            :disabled="selectedVideosIds.length == 0"
            @click="showModalPlugin = true"
          >
            <v-icon color="primary">mdi-plus</v-icon>
            {{ $t("video_view.run_plugin") }}
          </v-btn>
          <ModalPlugin v-model="showModalPlugin" :videoIds="selectedVideosIds" />
        </v-col>
      </v-row>

      <v-container class="d-flex flex-wrap video-gallery align-content-center">
        <v-card
          elevation="2"
          width="420px"
          v-for="item in videos"
          :loading="item.loading"
          :key="item.id"
        >
          <v-card-title class="video-overview-title mt-2 mb-2">
            {{ item.name }}
          </v-card-title>
          <v-card-text>
            <div>{{ $t("video_view.video_id") }} {{ item.id }}</div>
            <div>{{ $t("video_view.length") }} {{ getDisplayTime(item.duration) }}</div>
            <div>{{ $t("video_view.uploaded") }} {{ item.date.slice(0, 10) }}</div>
            <div>{{ $t("video_view.timelines") }} {{ item.num_timelines }}</div>

            <v-card-actions class="actions mt-n4 mb-n4">
              <v-btn variant="outlined" class="ml-n2" @click="showVideo(item.id)">
                <v-icon class="mr-1">
                  {{ "mdi-movie-search-outline" }}
                </v-icon>
                {{ $t("video_view.analysis") }}
              </v-btn>

              <ModalVideoRename :video="item.id" />

              <v-btn color="red" variant="outlined" @click="deleteVideo(item.id)">
                <v-icon class="mr-1">
                  {{ "mdi-trash-can-outline" }}
                </v-icon>
                {{ $t("video_view.delete") }}
              </v-btn>
              <v-checkbox v-model="selectedVideos[item.id]" color="primary" class="pt-5 ml-n1" />
            </v-card-actions>
          </v-card-text>
          <v-progress-linear v-model="videosProgress[item.id]" />
        </v-card>
      </v-container>
    </v-container>

    <v-container v-else>
      <v-col justify="space-around">
        <v-card class="welcome pa-5" elevation="3">
          <v-card-title>
            <h1 class="text-h2 mb-4 text-primary">{{ $t("welcome.title") }}</h1>
          </v-card-title>

          <v-card-text>
            <p v-html="$t('welcome.text')" class="mb-4"></p>
            <h2 class="text-h5 mb-2">{{ $t("welcome.demo_title") }}</h2>
            <p>
              <video id="welcome-video" controls>
                <source
                  src="https://tib.eu/cloud/s/sMmqWqWYict3Zpb/download/TIB-AV-A_Einfuehrung_2.mp4"
                  type="video/mp4"
                />
              </video>
            </p>
            <h2 class="text-h5 mb-1 mt-4">{{ $t("welcome.login_title") }}</h2>
            <p v-html="$t('welcome.login_text')" />
            <h2 class="text-h5 mb-1 mt-4">{{ $t("welcome.format_title") }}</h2>
            <p v-html="$t('welcome.format_text')" />
          </v-card-text>
        </v-card>
      </v-col>
    </v-container>
  </v-main>
</template>

<script setup>
import { ref, computed, onMounted, watch, watchEffect } from "vue";
import { useRouter } from "vue-router";
import { useVideoStore } from "@/stores/video";
import { useUserStore } from "@/stores/user";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useTimelineStore } from "@/stores/timeline";
import ModalPlugin from "@/components/ModalPlugin.vue";
import ModalVideoUpload from "@/components/ModalVideoUpload.vue";
import ModalVideoRename from "@/components/ModalVideoRename.vue";
import { getDisplayTime } from "@/plugins/time";

const router = useRouter();
const videoStore = useVideoStore();
const userStore = useUserStore();
const pluginRunStore = usePluginRunStore();
const timelineStore = useTimelineStore();

const showModalPlugin = ref(false);
const selectedVideos = ref({});
const fetchPluginTimer = ref(null);

const videos = computed(() => videoStore.all);
const selectedVideosIds = computed(() =>
  Object.entries(selectedVideos.value)
    .filter(([, isSelected]) => isSelected)
    .map(([id]) => id)
);

const videosProgress = computed(() => {
  const progress = {};
  videos.value.forEach((video) => {
    const runs = pluginRunStore.forVideo(video.id);
    progress[video.id] =
      (runs.filter((r) => r.status !== "RUNNING" && r.status !== "QUEUED").length / runs.length) *
      100;
  });
  return progress;
});

const fetchData = async (fetchTimelines = false) => {
  await videoStore.fetchAll();
  await pluginRunStore.fetchAll({ addResults: false });
  if (fetchTimelines) {
    await timelineStore.fetchAll({ addResultsType: true });
  }
};

const deleteVideo = (videoId) => videoStore.deleteVideo(videoId);
const showVideo = (videoId) => router.push({ path: `/video-analysis/${videoId}` });

onMounted(() => {
  fetchData();
});

watch(
  () => userStore.loggedIn,
  (newValue, oldValue) => {
    if (!oldValue && newValue) {
      fetchData();
    }
  }
);

watch(
  () => pluginRunStore.pluginInProgress,
  (newState) => {
    if (newState) {
      fetchPluginTimer.value = setInterval(() => {
        fetchData();
      }, 2000);
    } else if (fetchPluginTimer.value) {
      clearInterval(fetchPluginTimer.value);
    }
  },
  { immediate: true }
);
</script>

<style>
.video-overview-title {
  display: block !important;
  white-space: nowrap;
  overflow: hidden;
  width: 100%;
  text-overflow: ellipsis;
}

.video-gallery > * {
  margin: 8px;
}

.video-gallery > * {
  margin: 8px;
}

.actions > .v-btn:not(:first-child) {
  margin-left: 8px !important;
}
#welcome-video {
  margin-left: auto;
  margin-right: auto;
  display: block;
  border-style: outset;
  border-color: black;
  max-width: 800px;
}
</style>
