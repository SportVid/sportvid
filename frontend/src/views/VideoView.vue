<template>
  <v-main>
    <v-container v-if="userStore.loggedIn" fluid data-tour="video-select">
      <template v-if="hasNoVideos">
        <v-row class="empty-state-row" align="center">
          <v-col class="d-flex flex-column align-center justify-center">
            <v-card
              elevation="2"
              class="add-video-card"
              width="370"
              data-tour="modal-video-upload-open"
              @click="showModalVideoUpload = true"
            >
              <v-icon size="48" color="primary">mdi-plus</v-icon>
            </v-card>
            <div class="text-center mt-4 empty-state-text">
              <div class="text-h6 mb-1">{{ $t("video_view.empty_state_title") }}</div>
              <div class="text-body-2">{{ $t("video_view.empty_state_text") }}</div>
            </div>
          </v-col>
        </v-row>
      </template>
      <template v-else>
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
              <v-icon size="18" class="mr-2">
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

            <v-btn-toggle
              v-model="viewMode"
              mandatory
              density="compact"
              color="primary"
              variant="outlined"
              style="height: 40px"
            >
              <v-btn value="grid">
                <v-icon size="18">mdi-view-grid-outline</v-icon>
              </v-btn>
              <v-btn value="list">
                <v-icon size="18">mdi-view-sequential-outline</v-icon>
              </v-btn>
            </v-btn-toggle>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-container
              v-if="viewMode === 'grid'"
              class="d-flex flex-wrap justify-center video-gallery pa-0"
              fluid
            >
              <v-card
                elevation="2"
                class="add-video-card"
                width="370"
                data-tour="modal-video-upload-open"
                @click="showModalVideoUpload = true"
              >
                <v-icon size="48" color="primary">mdi-plus</v-icon>
              </v-card>
              <v-card
                elevation="2"
                v-for="item in videos"
                :loading="item.loading"
                :key="item.id"
                :class="showProcessingCard(item) ? 'processing-card' : 'video-card-clickable'"
                :data-tour="showProcessingCard(item) ? 'video-processing' : undefined"
                width="370"
                @click="!showProcessingCard(item) && showVideo(item.id)"
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
                  <v-spacer />
                  <v-menu
                    v-if="canWrite(item) && !showProcessingCard(item)"
                    location="bottom center"
                  >
                    <template #activator="{ props }">
                      <v-btn
                        icon="mdi-menu"
                        variant="text"
                        density="comfortable"
                        size="small"
                        v-bind="props"
                        @click.stop
                      />
                    </template>
                    <v-list density="compact" class="py-0">
                      <v-list-item @click="renameTargetId = item.id">
                        <v-list-item-title>{{ $t("video_view.rename_video") }}</v-list-item-title>
                      </v-list-item>
                      <v-list-item @click="deleteVideo(item.id)">
                        <v-list-item-title class="text-red">{{
                          $t("video_view.delete_video")
                        }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-menu>
                </v-card-title>
                <div v-if="showProcessingCard(item)" class="card-body card-body-processing">
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
                      @click.stop="deleteVideo(item.id)"
                    >
                      <v-icon class="mr-2">mdi-trash-can-outline</v-icon>
                      {{ $t("button.cancel_and_delete") }}
                    </v-btn>
                  </v-card-text>
                  <v-progress-linear
                    class="mt-auto"
                    :model-value="conversionProgress[item.id]"
                    :indeterminate="conversionIndeterminate(item)"
                  />
                </div>
                <div v-else class="card-body">
                  <div class="flip-container">
                    <div class="flip-inner" :class="{ flipped: flippedCards[item.id] }">
                      <div class="flip-face flip-front">
                        <img
                          v-if="videoCoverUrl[item.id]"
                          :src="videoCoverUrl[item.id]"
                          class="video-thumbnail"
                          alt=""
                        />
                        <div v-else class="video-thumbnail-placeholder">
                          <v-icon size="40" color="grey">mdi-movie-outline</v-icon>
                        </div>
                      </div>
                      <div class="flip-face flip-back">
                        <div class="info-rows">
                          <div class="info-row">{{ $t("video_view.video_id") }} {{ item.id }}</div>
                          <div class="info-row">
                            {{ $t("video_view.uploaded") }} {{ item.date.slice(0, 10) }}
                          </div>
                          <div class="info-row">
                            {{ $t("video_view.length") }} {{ getDisplayTime(item.duration) }}
                          </div>
                          <div class="info-row">
                            {{ $t("video_view.data") }}:
                            <span class="data-badges">
                              <span
                                v-for="cat in videoDataCategories[item.id]"
                                :key="cat.key"
                                class="data-badge"
                              >
                                <v-icon size="16" :color="stateColor(cat.state)">
                                  {{ stateIcon(cat.state) }}
                                </v-icon>
                                {{ cat.label }}
                              </span>
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="card-flip-toggle">
                    <v-btn
                      icon="mdi-dots-horizontal"
                      variant="text"
                      density="comfortable"
                      size="small"
                      @click.stop="toggleCardFlip(item.id)"
                    />
                  </div>
                  <v-progress-linear :model-value="videosProgress[item.id]" />
                </div>
              </v-card>
            </v-container>

            <div v-else class="video-list">
              <v-card
                elevation="2"
                class="add-video-card add-video-row"
                data-tour="modal-video-upload-open"
                @click="showModalVideoUpload = true"
              >
                <v-icon size="28" color="primary">mdi-plus</v-icon>
              </v-card>
              <v-card
                elevation="2"
                v-for="item in videos"
                :loading="item.loading"
                :key="item.id"
                :class="[
                  'video-row',
                  showProcessingCard(item) ? 'processing-card' : 'video-card-clickable',
                ]"
                :data-tour="showProcessingCard(item) ? 'video-processing' : undefined"
                @click="!showProcessingCard(item) && showVideo(item.id)"
              >
                <div class="video-row-main">
                  <div class="row-thumb">
                    <img
                      v-if="videoCoverUrl[item.id] && !showProcessingCard(item)"
                      :src="videoCoverUrl[item.id]"
                      class="row-thumbnail"
                      alt=""
                    />
                    <div v-else class="row-thumbnail-placeholder">
                      <i
                        v-if="showProcessingCard(item)"
                        class="mdi mdi-loading mdi-spin"
                        style="font-size: 26px"
                      />
                      <v-icon v-else size="26" color="grey">mdi-movie-outline</v-icon>
                    </div>
                  </div>

                  <div class="row-title-block">
                    <span class="title-name">{{ item.name }}</span>
                    <v-chip
                      v-if="item.owner_username && userStore.role === 'admin'"
                      size="x-small"
                      color="secondary"
                      class="ml-2 flex-shrink-0"
                      >{{ item.owner_username }}</v-chip
                    >
                  </div>

                  <v-spacer />

                  <template v-if="showProcessingCard(item)">
                    <span class="row-processing-text">{{ $t("video_view.video_processing") }}</span>
                    <v-btn
                      size="small"
                      color="red"
                      variant="outlined"
                      class="ml-3"
                      @click.stop="deleteVideo(item.id)"
                    >
                      <v-icon class="mr-2">mdi-trash-can-outline</v-icon>
                      {{ $t("button.cancel_and_delete") }}
                    </v-btn>
                  </template>
                  <div v-else class="row-actions">
                    <v-btn
                      :icon="expandedRows[item.id] ? 'mdi-chevron-up' : 'mdi-chevron-down'"
                      variant="text"
                      density="comfortable"
                      @click.stop="toggleRowExpand(item.id)"
                    />
                    <template v-if="canWrite(item)">
                      <v-btn
                        icon="mdi-pencil-outline"
                        variant="text"
                        density="comfortable"
                        @click.stop="renameTargetId = item.id"
                      />
                      <v-btn
                        icon="mdi-trash-can-outline"
                        variant="text"
                        density="comfortable"
                        color="red"
                        @click.stop="deleteVideo(item.id)"
                      />
                    </template>
                  </div>
                </div>

                <div
                  v-if="expandedRows[item.id] && !showProcessingCard(item)"
                  class="row-info"
                  @click.stop
                >
                  <v-divider class="mb-2" />
                  <div class="info-row">{{ $t("video_view.video_id") }} {{ item.id }}</div>
                  <div class="info-row">
                    {{ $t("video_view.uploaded") }} {{ item.date.slice(0, 10) }}
                  </div>
                  <div class="info-row">
                    {{ $t("video_view.length") }} {{ getDisplayTime(item.duration) }}
                  </div>
                  <div class="info-row">
                    {{ $t("video_view.data") }}:
                    <span class="data-badges">
                      <span
                        v-for="cat in videoDataCategories[item.id]"
                        :key="cat.key"
                        class="data-badge"
                      >
                        <v-icon size="16" :color="stateColor(cat.state)">
                          {{ stateIcon(cat.state) }}
                        </v-icon>
                        {{ cat.label }}
                      </span>
                    </span>
                  </div>
                </div>

                <v-progress-linear
                  :model-value="
                    showProcessingCard(item)
                      ? conversionProgress[item.id]
                      : videosProgress[item.id]
                  "
                  :indeterminate="showProcessingCard(item) && conversionIndeterminate(item)"
                />
              </v-card>
            </div>
          </v-col>
        </v-row>
      </template>
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

    <ModalVideoUpload v-if="showModalVideoUpload" v-model="showModalVideoUpload" />

    <ModalVideoRename
      v-if="renameTargetId !== null"
      :video="renameTargetId"
      v-model="renameDialogOpen"
    />
  </v-main>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useVideoStore } from "@/stores/video";
import { useUserStore } from "@/stores/user";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";
import { getDisplayTime } from "@/plugins/time";
import ModalVideoRename from "@/components/video/ModalVideoRename.vue";
import ModalVideoUpload from "@/components/video/ModalVideoUpload.vue";
import config from "../../app.config";

const router = useRouter();
const { t } = useI18n();
const videoStore = useVideoStore();
const userStore = useUserStore();
const pluginRunStore = usePluginRunStore();
const pluginRunResultStore = usePluginRunResultStore();

const showModalVideoUpload = ref(false);

const hasNoVideos = computed(() => videoStore.all.length === 0);

const filterName = ref("");
const filterSport = ref(null);
const filterAgeGroup = ref(null);
const sortDateDir = ref("desc");
const viewMode = computed({
  get: () => userStore.videoViewMode || "grid",
  set: (val) => userStore.saveVideoViewMode(val),
});

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

// Progress of the plugin batch currently being worked on for a video -- the mean over
// its runs, so three queued plugins with the first at 24% read as 8% instead of
// jumping in whole-run steps. Runs from an earlier session aren't part of a batch and
// therefore don't count (see pluginRunStore.batchProgress).
const videosProgress = computed(() => {
  const progress = {};
  videos.value.forEach((video) => {
    progress[video.id] = pluginRunStore.batchProgress(video.id);
  });
  return progress;
});

// Same slot, same meaning while a video is still being converted: how far along the
// work on this video is. Conversion and plugin runs never overlap.
const conversionProgress = computed(() => {
  const progress = {};
  videos.value.forEach((video) => {
    progress[video.id] = (parseFloat(video.progress) || 0) * 100;
  });
  return progress;
});

// ffmpeg only reports progress once the source duration is known, and the automatic
// thumbnail run afterwards has no percentage of its own -- show an indeterminate bar
// rather than a number that would sit still or lie.
const conversionIndeterminate = (item) => {
  if (!item.processing) return true;
  return !conversionProgress.value[item.id];
};

// Cover thumbnail shown on the front of a video card, sourced from the "thumbnail"
// plugin run that now runs automatically once a video finishes processing.
const latestThumbnailRun = (videoId) => {
  const runs = pluginRunStore.forVideo(videoId).filter((r) => r.type === "thumbnail");
  if (!runs.length) return null;
  return [...runs].sort((a, b) => new Date(b.date) - new Date(a.date))[0];
};

const thumbnailRunForVideo = (videoId) => {
  const run = latestThumbnailRun(videoId);
  return run && run.status === "DONE" ? run : null;
};

// Status of each video's latest thumbnail run. `videos` alone used to be enough as a
// watch source only because the 2-second refetch replaced every video object on each
// tick; with live updates the video object stays identical while only the run changes,
// so the run status has to be part of the source or the watchers below never fire.
const thumbnailRunStates = computed(() =>
  videos.value.map((item) => `${item.id}:${latestThumbnailRun(item.id)?.status ?? ""}`).join(",")
);

// Videos we've personally watched go through Video.status===PROCESSING in this session --
// only for those do we keep the "still processing" look alive while their automatic
// thumbnail generation finishes, so a card doesn't flash an empty placeholder right after
// upload. Pre-existing videos that loaded already-DONE show normally right away instead --
// there's no way to tell "thumbnail is about to arrive" apart from "predates this feature
// and never gets one" for those, so forcing the processing look on them would get stuck.
const observedProcessing = ref({});
watch(
  [videos, thumbnailRunStates],
  ([list]) => {
    // Both the "start tracking" and "stop tracking" writes live in this one watcher (not in
    // isThumbnailPending below) so it stays a pure read -- safe to call from several places
    // in the template per render without a mutation from one call leaking into the next.
    list.forEach((item) => {
      if (item.processing) {
        observedProcessing.value[item.id] = true;
        return;
      }
      if (!observedProcessing.value[item.id]) return;
      const run = latestThumbnailRun(item.id);
      if (run && run.status !== "RUNNING" && run.status !== "QUEUED") {
        delete observedProcessing.value[item.id];
      }
    });
  },
  { immediate: true }
);

const isThumbnailPending = (item) => {
  if (item.processing || !observedProcessing.value[item.id]) return false;
  const run = latestThumbnailRun(item.id);
  return !run || run.status === "RUNNING" || run.status === "QUEUED";
};

const showProcessingCard = (item) => item.processing || isThumbnailPending(item);

watch(
  [videos, thumbnailRunStates],
  ([list]) => {
    list.forEach((item) => {
      const run = thumbnailRunForVideo(item.id);
      if (!run) return;
      const existing = pluginRunResultStore.forPluginRun(run.id);
      if (existing.length === 0 || existing.some((r) => r.data === undefined)) {
        pluginRunResultStore.fetchForVideo({
          videoId: item.id,
          pluginRunId: run.id,
          addResults: true,
        });
      }
    });
  },
  { immediate: true }
);

const videoCoverUrl = computed(() => {
  const urls = {};
  videos.value.forEach((item) => {
    const run = thumbnailRunForVideo(item.id);
    const result =
      run && pluginRunResultStore.forPluginRun(run.id).find((r) => r.data?.images?.length);
    const image = result?.data.images[0];
    urls[item.id] = image
      ? `${config.THUMBNAIL_LOCATION}/${image.id.substr(0, 2)}/${image.id.substr(2, 2)}/${
          image.id
        }.${image.ext}`
      : null;
  });
  return urls;
});

const flippedCards = ref({});
const toggleCardFlip = (videoId) => {
  flippedCards.value = { ...flippedCards.value, [videoId]: !flippedCards.value[videoId] };
};

const expandedRows = ref({});
const toggleRowExpand = (videoId) => {
  expandedRows.value = { ...expandedRows.value, [videoId]: !expandedRows.value[videoId] };
};

// Compact position-data / metrics status per card, back of ModalStatus's status derivation but
// keyed by an arbitrary video id instead of the single currently-open player video. Manually
// uploaded tracking data is checked via video.has_tracking_data (a cheap server-side aggregate,
// see Video.to_dict()) rather than position_data.js's store, which only ever fetches for the
// single currently-open player video.
const POSDATA_TRACKER_TYPES = ["bytetrack", "object_tracker"];
const POSDATA_DLT_TYPES = ["calibration_static_dlt"];
const POSDATA_UPLOAD_TYPES = ["posdata_convert"];
const METRICS_TYPES = ["kpi_computation"];

const deriveRunState = (runs, types) => {
  const filtered = runs.filter((r) => types.includes(r.type));
  if (!filtered.length) return "none";
  if (filtered.some((r) => r.status === "DONE")) return "done";
  if (filtered.some((r) => r.status === "RUNNING" || r.status === "QUEUED")) return "running";
  if (filtered.some((r) => r.status === "ERROR")) return "error";
  return "none";
};

// AND: player tracking + DLT calibration belong together as one variant (ball tracking is
// optional, same as ModalStatus). OR: that variant vs. a manual upload are alternatives.
const combineAll = (states) => {
  if (states.every((s) => s === "done")) return "done";
  if (states.some((s) => s === "running")) return "running";
  if (states.some((s) => s === "error")) return "error";
  return "none";
};

const combineAny = (states) => {
  if (states.some((s) => s === "done")) return "done";
  if (states.some((s) => s === "running")) return "running";
  if (states.some((s) => s === "error")) return "error";
  return "none";
};

const posdataStates = computed(() => {
  const map = {};
  videos.value.forEach((item) => {
    const runs = pluginRunStore.forVideo(item.id);
    const autoState = combineAll([
      deriveRunState(runs, POSDATA_TRACKER_TYPES),
      deriveRunState(runs, POSDATA_DLT_TYPES),
    ]);
    const uploadState = item.has_tracking_data
      ? "done"
      : deriveRunState(runs, POSDATA_UPLOAD_TYPES);
    map[item.id] = combineAny([autoState, uploadState]);
  });
  return map;
});

const metricsStates = computed(() => {
  const map = {};
  videos.value.forEach((item) => {
    map[item.id] = deriveRunState(pluginRunStore.forVideo(item.id), METRICS_TYPES);
  });
  return map;
});

// Grouped under one "Daten:" row as a row of small status icons (see template) instead of one
// row per category -- keeps the card a fixed height as more categories (e.g. events) join later.
const videoDataCategories = computed(() => {
  const map = {};
  videos.value.forEach((item) => {
    map[item.id] = [
      {
        key: "posdata",
        label: t("modal.status.area.posdata"),
        state: posdataStates.value[item.id],
      },
      { key: "metrics", label: t("modal.status.area.kpi"), state: metricsStates.value[item.id] },
    ];
  });
  return map;
});

const stateColor = (state) => {
  if (state === "done") return "green";
  if (state === "running") return "blue";
  if (state === "error") return "red";
  return "grey";
};

const stateIcon = (state) => {
  const icons = {
    done: "mdi-checkbox-marked-circle-outline",
    running: "mdi-progress-clock",
    error: "mdi-alert-circle-outline",
    none: "mdi-checkbox-blank-circle-outline",
  };
  return icons[state] || icons.none;
};

// Initial load only -- conversion state and plugin run updates are pushed in over the
// live event stream afterwards (see stores/event_stream.js).
const fetchData = async () => {
  await videoStore.fetchAll();
  await pluginRunStore.fetchAll({ addResults: false });
};

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

const canWrite = (item) => {
  if (userStore.role === "admin") return true;
  return !item.owner_username || item.owner_username === userStore.username;
};

const deleteVideo = (videoId) => videoStore.deleteVideo(videoId);
const showVideo = (videoId) => router.push({ path: `/video-analysis/${videoId}` });

const renameTargetId = ref(null);
const renameDialogOpen = computed({
  get: () => renameTargetId.value !== null,
  set: (val) => {
    if (!val) renameTargetId.value = null;
  },
});

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
  margin-left: 4px;
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

.video-card-clickable {
  cursor: pointer;
  transition: box-shadow 0.2s ease;
}

.video-card-clickable:hover {
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.4) !important;
}

.card-body {
  height: 174px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.flip-container {
  flex: 1;
  min-height: 0;
  perspective: 1000px;
}

.flip-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.5s;
  transform-style: preserve-3d;
}

.flip-inner.flipped {
  transform: rotateY(180deg);
}

.flip-face {
  position: absolute;
  inset: 0;
  overflow: hidden;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.flip-front {
  display: flex;
  align-items: center;
  justify-content: center;
}

.flip-back {
  transform: rotateY(180deg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-thumbnail {
  height: 88%;
  object-fit: contain;
  border-radius: 5px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.video-thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-flip-toggle {
  display: flex;
  justify-content: center;
  flex-shrink: 0;
  height: 28px;
}

.info-rows {
  width: 100%;
  padding: 0 16px;
}

.info-row {
  display: flex;
  align-items: center;
  font-size: 0.9rem;
  line-height: 1.8;
}

.data-badges {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-left: 6px;
}

.data-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

.card-body-processing {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.add-video-card {
  cursor: pointer;
  height: 222px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed rgba(var(--v-theme-primary), 0.5);
  background: transparent;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.add-video-card:hover {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.05);
}

.empty-state-row {
  min-height: 70vh;
}

.empty-state-text {
  max-width: 380px;
}

.video-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.video-row {
  width: 100%;
}

.video-row-main {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
}

.row-thumb {
  width: 110px;
  height: 62px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.row-thumbnail {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 5px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.row-thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.row-title-block {
  display: flex;
  align-items: center;
  min-width: 0;
  flex-shrink: 1;
}

.row-title-block .title-name {
  font-size: 1.15rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.row-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 2px;
}

.row-actions :deep(.v-btn) {
  --v-btn-height: 36px;
}

.row-actions :deep(.v-icon) {
  font-size: 22px;
}

.row-processing-text {
  font-size: 1rem;
  color: rgba(var(--v-theme-on-surface), 0.7);
  white-space: nowrap;
}

.row-info {
  padding: 0 12px 12px 134px;
  cursor: default;
}

.row-info .info-row {
  font-size: 1.05rem;
}

.add-video-row {
  height: auto;
  min-height: 60px;
  padding: 8px 12px;
  flex-direction: row;
}
</style>
