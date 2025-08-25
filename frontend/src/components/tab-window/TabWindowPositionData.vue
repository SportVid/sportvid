<template>
  <PositionDataMenu v-if="Object.keys(topViewStore.positionDataTopView).length === 0" />

  <v-container v-else class="d-flex flex-column">
    <v-row class="mt-1" justify="center">
      <div style="position: relative; display: inline-block">
        <img
          ref="topViewElement"
          class="visualizer-image"
          :src="topViewStore.currentSport.pitchImage"
          @load="updateTopViewSize"
          :style="{
            maxHeight: maxVideoHeight * 100 + 'vh',
            height: videoStore.videoSize.height + 'px',
          }"
        />

        <div
          v-for="position in topViewStore.positionDataTopView[currentTime]"
          v-show="topViewStore.showItems"
          :key="position"
          :style="{
            position: 'absolute',
            width: '12px',
            height: '12px',
            borderRadius: '50%',
            transform: 'translate(-50%, -50%)',
            top:
              position.pos_y *
                (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
              'px',
            left:
              position.pos_x *
                (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
              'px',
            backgroundColor:
              !position.team_id || position.team_id === 'None' ? 'grey' : position.team_id,
          }"
        />

        <svg
          v-if="topViewStore.showEffectivePlayingSpace"
          :style="{
            position: 'absolute',
            top: '0px',
            left: '0px',
            width: topViewStore.topViewSize.width + 'px',
            height: topViewStore.topViewSize.height + 'px',
          }"
        >
          <polygon
            v-for="(hull, team) in convexHullPlayer[currentTime]"
            :key="team"
            :points="hull.map((p) => `${p.left},${p.top}`).join(' ')"
            :stroke="team"
            :fill="team"
            fill-opacity="0.4"
          />
        </svg>

        <svg
          v-if="topViewStore.showSpaceControl"
          :style="{
            position: 'absolute',
            top: '0px',
            left: '0px',
            width: topViewStore.topViewSize.width + 'px',
            height: topViewStore.topViewSize.height + 'px',
          }"
        >
          <polygon
            v-for="cell in voronoiCells[currentTime]"
            :key="cell"
            :points="cell.polygon.map((p) => `${p[0]},${p[1]}`).join(' ')"
            stroke="gray"
            :fill="cell.team_id"
            fill-opacity="0.4"
          />
        </svg>
      </div>
    </v-row>

    <v-row
      ref="videoControl"
      class="video-control mt-6 mb-n2 justify-center"
      data-tour="position-data-edit-row"
    >
      <v-menu location="top">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ topViewStore.currentSport.title }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact">
          <v-list-item
            v-for="item in topViewStore.sports"
            :key="item"
            class="menu-item"
            v-on:click="topViewStore.onSportChange(item.title)"
          >
            <v-list-item-title class="my-0">
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu location="top">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ $t("position_data.display_settings.title") }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact" width="225px">
          <v-list-item class="menu-item" @click="playerStore.viewBoundingBox">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("position_data.display_settings.view_bounding_box") }}
              <tab-window-icon
                :class="{
                  'text-disabled': !playerStore.showBoundingBox,
                  'text-red': playerStore.showBoundingBox,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="playerStore.toggleSliderSync">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("position_data.display_settings.video_sync") }}
              <tab-window-icon
                :class="{
                  'text-disabled': !playerStore.isSynced,
                  'text-red': playerStore.isSynced,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-menu location="end" open-on-hover>
            <template #activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.view_kpis.title") }}
                  <tab-window-icon>mdi-chevron-right</tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact" width="180px">
              <v-list-item class="menu-item" @click="topViewStore.viewSpaceControl">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.view_kpis.space_control") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !topViewStore.showSpaceControl,
                      'text-red': topViewStore.showSpaceControl,
                    }"
                  >
                    mdi-check
                  </tab-window-icon>
                </v-list-item-title>
              </v-list-item>
              <v-list-item class="menu-item" @click="topViewStore.viewEffectivePlayingSpace">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.view_kpis.eps") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !topViewStore.showEffectivePlayingSpace,
                      'text-red': topViewStore.showEffectivePlayingSpace,
                    }"
                  >
                    mdi-check
                  </tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>

          <v-menu location="end" open-on-hover>
            <template #activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.position_data.title") }}
                  <tab-window-icon>mdi-chevron-right</tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact">
              <v-list-item class="menu-item" @click="showModalPositionDataUpload = true">
                <v-list-item-title>
                  {{ $t("position_data.display_settings.position_data.upload") }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item class="menu-item" @click="showModalPositionDataSelect = true">
                <v-list-item-title>
                  {{ $t("position_data.display_settings.position_data.select") }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-list>
      </v-menu>
      <ModalPositionDataUpload
        v-if="showModalPositionDataUpload"
        v-model="showModalPositionDataUpload"
      />
      <ModalPositionDataSelect
        v-if="showModalPositionDataSelect"
        v-model="showModalPositionDataSelect"
      />

      <div class="time-code ml-2">
        {{ getTimecode(currentTime) }}
      </div>
    </v-row>

    <v-row ref="videoSlider">
      <v-slider
        v-model="currentTime"
        @update:model-value="onProgressChange"
        hide-details
        color="primary"
        :disabled="playerStore.isSynced"
        :thumb-size="15"
        :step="1000 / playerStore.videoFPS"
        min="0"
        :max="playerStore.videoDuration"
      />
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import { useBboxesStore } from "@/stores/bboxes";
import { useVideoStore } from "@/stores/video";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { getTimecode } from "@/plugins/time";
import { Delaunay } from "d3-delaunay";
import PositionDataMenu from "@/components/position-data/PositionDataMenu.vue";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";

const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const bboxesStore = useBboxesStore();
const videoStore = useVideoStore();
const calibrationAssetStore = useCalibrationAssetStore();

const showModalPositionDataSelect = ref(false);
const showModalPositionDataUpload = ref(false);

const progress = ref(0);
const currentTime = computed({
  get() {
    return playerStore.isSynced ? playerStore.currentTime : progress.value;
  },
  set(val) {
    if (!playerStore.isSynced) {
      progress.value = Math.round(val);
    }
  },
});
const onProgressChange = (time) => {
  if (!playerStore.isSynced) {
    progress.value = Math.round(time);
  }
};
watch(
  () => playerStore.isSynced,
  (isSynced) => {
    if (!isSynced) {
      progress.value = playerStore.currentTime;
    }
  }
);
watch(
  () => progress.value,
  (newTime) => {
    console.log("Progress changed:", newTime);
  }
);

const topViewElement = ref(null);
const updateTopViewSize = async () => {
  await nextTick();
  await waitForStableElement(topViewElement);

  if (topViewElement.value) {
    const rect = topViewElement.value.getBoundingClientRect();
    topViewStore.setTopViewSize({
      width: rect.width,
      height: rect.height,
      top: rect.top,
      left: rect.left,
    });
  }
};
function waitForStableElement(elRef) {
  return new Promise((resolve) => {
    let lastRect = null;
    let stableCounter = 0;

    const check = () => {
      const el = elRef.value;
      if (!el) {
        requestAnimationFrame(check);
        return;
      }

      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0 || rect.top === 0 || rect.left === 0) {
        requestAnimationFrame(check);
        return;
      }

      if (
        lastRect &&
        rect.top === lastRect.top &&
        rect.left === lastRect.left &&
        rect.width === lastRect.width &&
        rect.height === lastRect.height
      ) {
        stableCounter++;
      } else {
        stableCounter = 0;
      }

      lastRect = rect;

      if (stableCounter >= 3) {
        resolve();
      } else {
        requestAnimationFrame(check);
      }
    };

    check();
  });
}
const resizeObserver = new ResizeObserver(() => {
  updateTopViewSize();
});
onMounted(() => {
  window.addEventListener("resize", updateTopViewSize);
  if (topViewElement.value) {
    resizeObserver.observe(topViewElement.value);
    updateTopViewSize();
  }
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTopViewSize);
  if (topViewElement.value) {
    resizeObserver.unobserve(topViewElement.value);
  }
});

const computeConvexHull = (points) => {
  if (points.length < 3) return [];
  const sortedPoints = points.slice().sort((a, b) => a.left - b.left || a.top - b.top);

  const cross = (o, a, b) =>
    (a.left - o.left) * (b.top - o.top) - (a.top - o.top) * (b.left - o.left);

  const lower = [];
  for (const p of sortedPoints) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
      lower.pop();
    }
    lower.push(p);
  }

  const upper = [];
  for (let i = sortedPoints.length - 1; i >= 0; i--) {
    const p = sortedPoints[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
      upper.pop();
    }
    upper.push(p);
  }

  lower.pop();
  upper.pop();

  return lower.concat(upper);
};
const convexHullPlayer = computed(() => {
  if (!topViewStore.topViewSize || !topViewStore.positionDataTopView) {
    return {};
  }
  const result = {};
  Object.entries(topViewStore.positionDataTopView).forEach(([timeKey, framePositions]) => {
    const teams = {};
    framePositions
      .filter((position) => position.team_id === "red" || position.team_id === "blue")
      .forEach((position) => {
        const top =
          position.pos_y * topViewStore.topViewSize.height * topViewStore.currentSport.heightRel +
          ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height;
        const left =
          position.pos_x * topViewStore.topViewSize.width * topViewStore.currentSport.widthRel +
          ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width;
        if (!teams[position.team_id]) {
          teams[position.team_id] = [];
        }
        teams[position.team_id].push({ left, top });
      });
    const hulls = {};
    Object.keys(teams).forEach((team) => {
      const points = teams[team];
      hulls[team] = points.length >= 3 ? computeConvexHull(points) : points;
    });
    result[timeKey] = hulls;
  });
  return result;
});

const computeVoronoi = (players) => {
  if (!players.length) return [];

  const delaunay = Delaunay.from(players.map((p) => [p.left, p.top]));
  const voronoi = delaunay.voronoi([
    ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width,

    ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height,

    ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
      topViewStore.topViewSize.width * topViewStore.currentSport.widthRel,

    ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
      topViewStore.topViewSize.height * topViewStore.currentSport.heightRel,
  ]);

  return players
    .map((player, i) => {
      const polygon = voronoi.cellPolygon(i);
      return polygon ? { team_id: player.team_id, polygon } : null;
    })
    .filter((cell) => cell !== null);
};
const voronoiCells = computed(() => {
  if (!topViewStore.topViewSize || !topViewStore.positionDataTopView) {
    return {};
  }
  const result = {};
  Object.entries(topViewStore.positionDataTopView).forEach(([timeKey, framePositions]) => {
    const allPlayers = framePositions
      .filter((player) => player.team_id === "red" || player.team_id === "blue")
      .map((player) => {
        const top =
          player.pos_y * topViewStore.topViewSize.height * topViewStore.currentSport.heightRel +
          ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height;
        const left =
          player.pos_x * topViewStore.topViewSize.width * topViewStore.currentSport.widthRel +
          ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width;
        return { left, top, team_id: player.team_id };
      });
    result[timeKey] = computeVoronoi(allPlayers);
  });
  return result;
});

console.log("KPIs", convexHullPlayer.value, voronoiCells.value);

const maxVideoHeight = ref(0);
const videoSlider = ref(null);
const videoControl = ref(null);
const updateMaxHeight = () => {
  if (!videoSlider.value || !videoControl.value) return;
  maxVideoHeight.value =
    (window.innerHeight -
      104 -
      32 -
      videoSlider.value.$el.offsetHeight -
      videoControl.value.$el.offsetHeight -
      60) /
    window.innerHeight;
};
onMounted(() => {
  nextTick(() => updateMaxHeight());
  window.addEventListener("resize", updateMaxHeight);
});
watch(() => window.innerHeight, updateMaxHeight);
watch(videoControl || videoSlider, (newVal) => {
  if (newVal) {
    nextTick(() => updateMaxHeight());
  }
});
</script>

<style scoped>
.visualizer-image {
  max-width: 100%;
  max-height: 100%;
}

.video-control {
  gap: 5px;
}

.video-control > .time-code {
  margin-top: auto;
  margin-bottom: auto;
}

.menu-item {
  cursor: pointer;
}

.menu-item:hover {
  background-color: #f0f0f0;
}

.menu-item .v-list-item-title {
  font-size: 12px;
}
</style>
