<template>
  <div v-if="!bboxesStore.bboxDataLoaded" style="height: 60vh">
    <v-col>
      <v-row
        class="text-h6 text-grey font-weight-light mx-16 px-10 mt-8"
        style="
          align-items: center;
          justify-content: center;
          text-align: center;
          line-height: 1.5;
          height: 30vh;
        "
        v-html="$t('pos_data_vis.no_bbox_data')"
      />
      <v-row style="justify-content: center">
        <v-btn>Upload position data</v-btn>
      </v-row>
    </v-col>
  </div>

  <v-container v-else class="d-flex flex-column">
    <v-row class="mt-1" justify="center">
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

      <!-- <div
        v-for="(position, index) in bboxesStore.positionsNested[sliderValue]"
        :key="index"
        class="data-point-position"
        :style="{
          top:
            (position.bbox_top + position.bbox_height) *
              (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
            (topViewStore.topViewSize.top +
              ((1 - topViewStore.currentSport.heightRel) / 2) *
                topViewStore.topViewSize.height) +
            'px',
          left:
            (position.bbox_left + position.bbox_width / 2) *
              (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
            (topViewStore.topViewSize.left +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width) +
            'px',
          backgroundColor: `${position.team}`,
        }"
      /> -->
      <div
        v-for="(position, index) in bboxesStore.positionsFlat.filter(
          (p) => p.image_id === sliderValue
        )"
        :key="index"
        class="data-point-position"
        :style="{
          top:
            (position.y + position.h) *
              (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
            (topViewStore.topViewSize.top +
              ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height) +
            'px',
          left:
            (position.x + position.w / 2) *
              (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
            (topViewStore.topViewSize.left +
              ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width) +
            'px',
          backgroundColor: position.team,
        }"
      />

      <svg v-if="bboxesStore.showEffectivePlayingSpace" class="hull-overlay">
        <polygon
          v-for="(hull, team) in convexHullPlayer[sliderValue]"
          :key="team"
          :points="hull.map((p) => `${p.left},${p.top}`).join(' ')"
          :stroke="team"
          :fill="team"
          fill-opacity="0.4"
        />
      </svg>

      <svg v-if="bboxesStore.showSpaceControl" class="voronoi-overlay">
        <polygon
          v-for="(cell, index) in voronoiCells[sliderValue]"
          :key="index"
          :points="cell.polygon.map((p) => `${p[0]},${p[1]}`).join(' ')"
          stroke="gray"
          :fill="cell.team"
          fill-opacity="0.4"
        />
      </svg>
    </v-row>

    <v-row ref="videoControl" class="video-control mt-6 mb-n1">
      <v-menu location="top">
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ topViewStore.currentSport.title }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact">
          <v-list-item
            v-for="(item, index) in topViewStore.sports"
            :key="index"
            class="menu-item"
            v-on:click="topViewStore.onSportChange(index)"
          >
            <v-list-item-title class="my-0">
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu location="top">
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ $t("pos_data_vis.display_settings.title") }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact">
          <v-list-item class="menu-item" @click="bboxesStore.viewBoundingBox">
            <v-list-item-title>
              {{ $t("pos_data_vis.display_settings.view_bounding_box") }}
              <v-icon
                :class="{
                  'text-disabled': !bboxesStore.showBoundingBox,
                  'text-red': bboxesStore.showBoundingBox,
                }"
                class="ml-12 mb-1"
                size="small"
              >
                mdi-check
              </v-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="playerStore.toggleSliderSync">
            <v-list-item-title>
              {{ $t("pos_data_vis.display_settings.video_sync") }}
              <v-icon
                :class="{
                  'text-disabled': !playerStore.isSynced,
                  'text-red': playerStore.isSynced,
                }"
                class="ml-12 mb-1"
                size="small"
              >
                mdi-check
              </v-icon>
            </v-list-item-title>
          </v-list-item>

          <v-menu location="end" open-on-hover>
            <template v-slot:activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title>
                  {{ $t("pos_data_vis.display_settings.view_kpis.title") }}
                  <v-icon class="ml-5 mb-1" size="small">mdi-chevron-right</v-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact">
              <v-list-item class="menu-item" @click="bboxesStore.viewSpaceControl">
                <v-list-item-title>
                  {{ $t("pos_data_vis.display_settings.view_kpis.space_control") }}
                  <v-icon
                    :class="{
                      'text-disabled': !bboxesStore.showSpaceControl,
                      'text-red': bboxesStore.showSpaceControl,
                    }"
                    class="ml-4 mb-1"
                    size="small"
                  >
                    mdi-check
                  </v-icon>
                </v-list-item-title>
              </v-list-item>
              <v-list-item class="menu-item" @click="bboxesStore.viewEffectivePlayingSpace">
                <v-list-item-title>
                  {{ $t("pos_data_vis.display_settings.view_kpis.eps") }}
                  <v-icon
                    :class="{
                      'text-disabled': !bboxesStore.showEffectivePlayingSpace,
                      'text-red': bboxesStore.showEffectivePlayingSpace,
                    }"
                    class="ml-4 mb-1"
                    size="small"
                  >
                    mdi-check
                  </v-icon>
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>

          <v-menu location="end" open-on-hover>
            <template v-slot:activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title>
                  {{ $t("pos_data_vis.display_settings.pos_data.title") }}
                  <v-icon class="ml-16 pl-10 mb-1" size="small">mdi-chevron-right</v-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact">
              <v-list-item class="menu-item">
                <v-list-item-title>
                  {{ $t("pos_data_vis.display_settings.pos_data.upload") }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item class="menu-item" @click="showModalBboxDataSelect = true">
                <v-list-item-title>
                  {{ $t("pos_data_vis.display_settings.pos_data.select") }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-list>
      </v-menu>
      <ModalBboxDataSelect v-model="showModalBboxDataSelect" />

      <div class="time-code flex-grow-1 flex-shrink-0 ml-2">
        {{ getTimecode(sliderValue) }}
      </div>
    </v-row>

    <v-row ref="videoSlider">
      <v-slider
        v-model="sliderValue"
        @update:model-value="updateFrame"
        hide-details
        color="primary"
        :thumb-size="15"
        :max="99"
        :step="1"
        :disabled="playerStore.isSynced"
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
import { getTimecode } from "@/plugins/time";
import { Delaunay } from "d3-delaunay";
import ModalBboxDataSelect from "@/components/ModalBboxDataSelect.vue";

const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const bboxesStore = useBboxesStore();
const videoStore = useVideoStore();

const showModalBboxDataSelect = ref(false);

const topViewElement = ref(null);

const currentFrame = ref(0);
const updateFrame = (newIndex) => {
  currentFrame.value = newIndex;
};
const currentTime = computed(() => playerStore.currentTime);

const sliderValue = computed({
  get: () => {
    return playerStore.isSynced ? Math.round(currentTime.value) : currentFrame.value;
  },
  set: (value) => {
    if (!playerStore.isSynced) {
      currentFrame.value = value;
      updateFrame(value);
    }
  },
});

const updateTopViewSize = () => {
  nextTick(() => {
    if (topViewElement.value) {
      const rect = topViewElement.value.getBoundingClientRect();
      topViewStore.setTopViewSize({
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      });
    }
  });
};
onMounted(() => {
  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
  }, 500);
  updateTopViewSize();
  window.addEventListener("resize", updateTopViewSize);
  window.addEventListener("scroll", updateTopViewSize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTopViewSize);
  window.removeEventListener("scroll", updateTopViewSize);
});

const computeConvexHull = (points) => {
  if (points.length < 3) return [];

  points = [...points].sort((a, b) => a.left - b.left || a.top - b.top);

  const cross = (o, a, b) =>
    (a.left - o.left) * (b.top - o.top) - (a.top - o.top) * (b.left - o.left);

  const lower = [];
  for (const p of points) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
      lower.pop();
    }
    lower.push(p);
  }

  const upper = [];
  for (let i = points.length - 1; i >= 0; i--) {
    const p = points[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
      upper.pop();
    }
    upper.push(p);
  }

  upper.pop();
  lower.pop();

  return lower.concat(upper);
};
const convexHullPlayer = computed(() => {
  if (!topViewStore.topViewSize || !bboxesStore.positionsNested) {
    return [];
  }

  return bboxesStore.positionsNested.map((framePositions) => {
    const teams = {};

    framePositions.forEach((position) => {
      if (!teams[position.team]) {
        teams[position.team] = [];
      }
      teams[position.team].push({
        top:
          (position.bbox_top + position.bbox_height) *
            (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
          (topViewStore.topViewSize.top +
            ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height),
        left:
          (position.bbox_left + position.bbox_width / 2) *
            (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
          (topViewStore.topViewSize.left +
            ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width),
      });
    });

    return Object.keys(teams).reduce((acc, team) => {
      acc[team] = computeConvexHull(teams[team]);
      return acc;
    }, {});
  });
});

const computeVoronoi = (players) => {
  if (!players.length) return [];

  const delaunay = Delaunay.from(players.map((p) => [p.left, p.top]));
  const voronoi = delaunay.voronoi([
    topViewStore.topViewSize.left +
      ((1 - topViewStore.currentSport.widthRel) / 2) * compAreatopViewStoreStore.topViewSize.width,
    topViewStore.topViewSize.top +
      ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height,
    topViewStore.topViewSize.left +
      ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
      topViewStore.topViewSize.width * topViewStore.currentSport.widthRel,
    topViewStore.topViewSize.top +
      ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
      topViewStore.topViewSize.height * topViewStore.currentSport.heightRel,
  ]);

  return players
    .map((player, i) => {
      const polygon = voronoi.cellPolygon(i);
      return polygon ? { team: player.team, polygon } : null;
    })
    .filter((cell) => cell !== null);
};
const voronoiCells = computed(() => {
  if (!topViewStore.topViewSize || !bboxesStore.positionsNested) {
    return [];
  }

  return bboxesStore.positionsNested.map((framePositions) => {
    const allPlayers = framePositions.map((player) => ({
      top:
        (player.bbox_top + player.bbox_height) *
          topViewStore.topViewSize.height *
          topViewStore.currentSport.heightRel +
        (topViewStore.topViewSize.top +
          ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height),
      left:
        (player.bbox_left + player.bbox_width / 2) *
          topViewStore.topViewSize.width *
          topViewStore.currentSport.widthRel +
        (topViewStore.topViewSize.left +
          ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width),
      team: player.team,
    }));

    return computeVoronoi(allPlayers);
  });
});

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
</script>

<style>
.visualizer-image {
  max-width: 100%;
  max-height: 100%;
}

.data-point-position {
  position: fixed;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
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

.hull-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}

.voronoi-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}
</style>
