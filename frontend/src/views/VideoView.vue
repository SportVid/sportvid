<template>
  <v-main>
    <v-container v-if="userStore.loggedIn" fluid data-tour="video-select">
      <v-row class="mb-n2">
        <v-col class="d-flex flex-wrap justify-center align-center pb-0" style="gap: 8px">
          <v-text-field
            v-model="filterName"
            :label="$t('video_view.filter_name')"
            density="compact"
            variant="outlined"
            color="primary"
            base-color="primary"
            hide-details
            clearable
            prepend-inner-icon="mdi-magnify"
            style="max-width: 280px"
          />
          <v-select
            v-model="filterSport"
            :items="sportOptions"
            :label="$t('video_view.filter_sport')"
            density="compact"
            variant="outlined"
            color="primary"
            base-color="primary"
            hide-details
            clearable
            style="max-width: 240px"
          />
          <v-select
            v-model="filterAgeGroup"
            :items="ageGroupOptions"
            :label="$t('video_view.filter_age_group')"
            density="compact"
            variant="outlined"
            color="primary"
            base-color="primary"
            hide-details
            clearable
            style="max-width: 240px"
          />
          <v-btn
            variant="outlined"
            color="primary"
            density="compact"
            @click="toggleDateSort"
            class="text-none"
            style="height: 40px"
          >
            <v-icon size="18" class="mr-1">
              {{
                sortDateDir === "desc"
                  ? "mdi-sort-calendar-descending"
                  : "mdi-sort-calendar-ascending"
              }}
            </v-icon>
            {{
              sortDateDir === "desc"
                ? $t("video_view.sort_date_newest")
                : $t("video_view.sort_date_oldest")
            }}
          </v-btn>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-container class="d-flex flex-wrap justify-center video-gallery pa-0" fluid>
            <v-card
              elevation="2"
              v-for="item in videos"
              :loading="item.loading"
              :key="item.id"
              :class="item.processing ? 'processing-card' : ''"
              :data-tour="item.processing ? 'video-processing' : undefined"
              width="370"
            >
              <v-card-title class="video-overview-title mt-2 mb-n2">
                <span class="title-name">{{ item.name }}</span>
                <v-chip
                  v-if="item.owner_username && userStore.role === 'admin'"
                  size="x-small"
                  color="secondary"
                  class="ml-2 flex-shrink-0"
                  >{{ item.owner_username }}</v-chip
                >
              </v-card-title>
              <div v-if="item.processing" class="card-body card-body-processing">
                <v-card-text class="d-flex flex-column align-center py-3">
                  <i class="mdi mdi-loading mdi-spin" style="font-size: 40px" />
                  <div class="mt-2">
                    {{ $t("video_view.video_processing") }}
                  </div>
                  <v-btn
                    size="small"
                    color="red"
                    variant="outlined"
                    class="mt-3"
                    @click="deleteVideo(item.id)"
                  >
                    <v-icon class="mr-1">mdi-trash-can-outline</v-icon>
                    {{ $t("button.cancel_and_delete") }}
                  </v-btn>
                </v-card-text>
              </div>
              <div v-else class="card-body">
                <v-card-text class="card-text-inner">
                  <div>{{ $t("video_view.video_id") }} {{ item.id }}</div>
                  <div>{{ $t("video_view.length") }} {{ getDisplayTime(item.duration) }}</div>
                  <div>{{ $t("video_view.uploaded") }} {{ item.date.slice(0, 10) }}</div>
                  <div>{{ $t("video_view.timelines") }} {{ item.num_timelines }}</div>
                </v-card-text>
                <div
                  :class="
                    canWrite(item) ? 'card-actions-row' : 'card-actions-row card-actions-row-solo'
                  "
                >
                  <v-tooltip :text="$t('button.analyse')" location="top">
                    <template #activator="{ props }">
                      <v-btn variant="outlined" v-bind="props" @click="showVideo(item.id)">
                        <v-icon>mdi-movie-search-outline</v-icon>
                      </v-btn>
                    </template>
                  </v-tooltip>

                  <ModalVideoRename v-if="canWrite(item)" :video="item.id" />

                  <v-tooltip v-if="canWrite(item)" :text="$t('button.delete')" location="top">
                    <template #activator="{ props }">
                      <v-btn
                        color="red"
                        variant="outlined"
                        v-bind="props"
                        @click="deleteVideo(item.id)"
                      >
                        <v-icon>mdi-trash-can-outline</v-icon>
                      </v-btn>
                    </template>
                  </v-tooltip>

                  <v-checkbox
                    v-if="canWrite(item)"
                    v-model="videoStore.selectedVideos[item.id]"
                    color="primary"
                    class="ml-n1"
                    hide-details
                  />
                </div>
                <v-progress-linear v-model="videosProgress[item.id]" />
              </div>
            </v-card>
          </v-container>
        </v-col>
      </v-row>
    </v-container>

    <v-container v-else>
      <v-col justify="space-around">
        <v-card class="welcome pa-5" elevation="3">
          <v-card-title>
            <h1 class="text-h2 mb-4 text-primary">{{ $t("plattform.title") }}</h1>
          </v-card-title>

          <v-card-text>
            <p v-html="$t('welcome.text')" class="mb-4"></p>
            <h2 class="text-h5 mb-2">{{ $t("welcome.demo_title") }}</h2>
            <p>
              <video class="welcome-video" controls>
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

    <v-snackbar v-model="showLogoutSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon-success />
        <span class="text-h6">{{ $t("user.logout.success") }}</span>
      </div>
    </v-snackbar>

    <v-snackbar v-model="showAccountDeletedSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon-success />
        <span class="text-h6">{{ $t("modal.delete_account.success") }}</span>
      </div>
    </v-snackbar>

    <v-snackbar v-model="showVideoActionSnackbar">
      <div class="d-flex justify-center">
        <snackbar-icon-success />
        <span class="text-h6">{{ videoActionMessage }}</span>
      </div>
    </v-snackbar>
  </v-main>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useVideoStore } from "@/stores/video";
import { useUserStore } from "@/stores/user";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useTimelineStore } from "@/stores/timeline";
import { getDisplayTime } from "@/plugins/time";
import ModalVideoRename from "@/components/video/ModalVideoRename.vue";

const router = useRouter();
const { t } = useI18n();
const videoStore = useVideoStore();
const userStore = useUserStore();
const pluginRunStore = usePluginRunStore();
const timelineStore = useTimelineStore();

const filterName = ref("");
const filterSport = ref(null);
const filterAgeGroup = ref(null);
const sortDateDir = ref("desc");

const toggleDateSort = () => {
  sortDateDir.value = sortDateDir.value === "desc" ? "asc" : "desc";
};

const sportOptions = computed(() => {
  const unique = [...new Set(videoStore.all.map((v) => v.sport).filter(Boolean))];
  return unique.map((s) => ({ title: t(`sports.${s}.title`, s), value: s }));
});

const ageGroupOptions = computed(() => {
  const unique = [...new Set(videoStore.all.map((v) => v.age_group).filter(Boolean))];
  return unique.map((a) => ({ title: t(`modal.video.upload.age_groups.${a}`, a), value: a }));
});

const videos = computed(() => {
  let list = videoStore.all;
  if (filterName.value) {
    const q = filterName.value.toLowerCase();
    list = list.filter((v) => v.name?.toLowerCase().includes(q));
  }
  if (filterSport.value) list = list.filter((v) => v.sport === filterSport.value);
  if (filterAgeGroup.value) list = list.filter((v) => v.age_group === filterAgeGroup.value);
  return [...list].sort((a, b) => {
    const diff = new Date(b.date) - new Date(a.date);
    return sortDateDir.value === "desc" ? diff : -diff;
  });
});

const videosProgress = computed(() => {
  const progress = {};
  videos.value.forEach((video) => {
    const runs = pluginRunStore.forVideo(video.id);
    if (runs.length === 0) {
      progress[video.id] = 0;
    } else {
      progress[video.id] =
        (runs.filter((r) => r.status !== "RUNNING" && r.status !== "QUEUED").length / runs.length) *
        100;
    }
  });
  return progress;
});
watch(
  videosProgress,
  (newState, oldState) => {
    if (!oldState) return;
    if (Object.keys(newState).some((k) => oldState[k] !== newState[k])) {
      fetchData(true);
    }
  },
  { deep: true }
);

const fetchPluginTimer = ref(null);
const fetchData = async (fetchTimelines = false) => {
  await videoStore.fetchAll();
  await pluginRunStore.fetchAll({ addResults: false });
  if (fetchTimelines) {
    await timelineStore.fetchAll({ addResultsType: true });
  }
};

const processingPollTimer = ref(null);
const hasProcessingVideos = computed(() => {
  return videos.value.some((v) => v.processing === true);
});
watch(
  hasProcessingVideos,
  (newVal) => {
    if (newVal) {
      if (processingPollTimer.value) clearInterval(processingPollTimer.value);
      processingPollTimer.value = setInterval(() => fetchData(), 2000);
    } else if (processingPollTimer.value) {
      clearInterval(processingPollTimer.value);
      processingPollTimer.value = null;
    }
  },
  { immediate: true }
);
onUnmounted(() => {
  if (processingPollTimer.value) clearInterval(processingPollTimer.value);
  if (fetchPluginTimer.value) clearInterval(fetchPluginTimer.value);
});

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

const canWrite = (item) => {
  if (userStore.role === "admin") return true;
  return !item.owner_username || item.owner_username === userStore.username;
};

const deleteVideo = (videoId) => videoStore.deleteVideo(videoId);
const showVideo = (videoId) => router.push({ path: `/video-analysis/${videoId}` });

const showLogoutSnackbar = ref(false);
watch(
  () => userStore.loggedIn,
  (newValue, oldValue) => {
    if (oldValue === true && newValue === false) {
      // If the account was deleted, show account-deleted snackbar instead of logout
      if (!userStore.accountDeleted) {
        showLogoutSnackbar.value = true;
      }
    }
  }
);

const showAccountDeletedSnackbar = ref(false);
const resetAccountDeletedSnackbar = async () => {
  showAccountDeletedSnackbar.value = false;
  await nextTick();
  showAccountDeletedSnackbar.value = true;
};
watch(
  () => userStore.accountDeleted,
  (val) => {
    if (val) {
      resetAccountDeletedSnackbar();
      userStore.accountDeleted = false;
    }
  }
);

const showVideoActionSnackbar = ref(false);
const videoActionMessage = ref("");
const resetVideoActionSnackbar = async () => {
  showVideoActionSnackbar.value = false;
  await nextTick();
  showVideoActionSnackbar.value = true;
};
watch(
  [() => videoStore.uploadSuccess, () => videoStore.renameSuccess, () => videoStore.deleteSuccess],
  ([upload, rename, del]) => {
    if (upload === true) {
      videoActionMessage.value = t("modal.video.upload.success");
      resetVideoActionSnackbar();
      videoStore.uploadSuccess = false;
    } else if (rename === true) {
      videoActionMessage.value = t("modal.video.rename.success");
      resetVideoActionSnackbar();
      videoStore.renameSuccess = false;
    } else if (del === true) {
      videoActionMessage.value = t("modal.video.delete.success");
      resetVideoActionSnackbar();
      videoStore.deleteSuccess = false;
    }
  }
);
</script>

<style scoped>
.video-overview-title {
  display: flex !important;
  align-items: center;
  overflow: hidden;
  width: 100%;
}

.title-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.video-gallery > * {
  margin: 8px;
}

.welcome-video {
  margin-left: auto;
  margin-right: auto;
  display: block;
  border-style: outset;
  border-color: black;
  max-width: 800px;
}

.processing-card {
  opacity: 0.6;
}

.card-body {
  height: 174px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-text-inner {
  flex: 1;
  padding-bottom: 4px !important;
}

.card-actions-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 0 8px 6px;
  flex-shrink: 0;
}

.card-actions-row-solo {
  padding-bottom: 14px;
}

.card-body-processing {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
</style>
