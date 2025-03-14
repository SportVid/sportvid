<template>
  <v-container class="d-flex flex-column">
    <v-row class="mt-1">
      <img
        ref="compAreaElement"
        class="visualizer-image"
        :src="compAreaStore.currentSport.pitchImage"
        @load="updateCompAreaSize"
      />

      <div
        v-for="(position, index) in markerStore.positions[sliderValue]"
        :key="index"
        class="data-point-position"
        :style="{
          top:
            (position.bbox_top + position.bbox_height) *
              (compAreaStore.compAreaSize.height * compAreaStore.currentSport.heightRel) +
            (compAreaStore.compAreaSize.top +
              ((1 - compAreaStore.currentSport.heightRel) / 2) *
                compAreaStore.compAreaSize.height) +
            'px',
          left:
            (position.bbox_left + position.bbox_width / 2) *
              (compAreaStore.compAreaSize.width * compAreaStore.currentSport.widthRel) +
            (compAreaStore.compAreaSize.left +
              ((1 - compAreaStore.currentSport.widthRel) / 2) * compAreaStore.compAreaSize.width) +
            'px',
          backgroundColor: `${position.team}`,
        }"
      />

      <svg v-if="markerStore.showEffectivePlayingSpace" class="hull-overlay">
        <polygon
          v-for="(hull, team) in convexHullPlayer[sliderValue]"
          :key="team"
          :points="hull.map((p) => `${p.left},${p.top}`).join(' ')"
          :stroke="team"
          :fill="team"
          fill-opacity="0.4"
        />
      </svg>

      <svg v-if="markerStore.showSpaceControl" class="voronoi-overlay">
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

    <v-row class="video-control mt-6 mb-n1">
      <v-menu offset-y top>
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ compAreaStore.currentSport.title }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact">
          <v-list-item
            v-for="(item, index) in compAreaStore.sports"
            :key="index"
            class="menu-item"
            v-on:click="compAreaStore.onSportChange(index)"
          >
            <v-list-item-title class="my-0">
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu offset-y top>
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" size="small">
            <v-icon>mdi-dots-horizontal</v-icon>
          </v-btn>
        </template>
        <v-list class="py-0" density="compact">
          <v-list-item class="menu-item" @click="markerStore.viewBoundingBox">
            <v-list-item-title>
              {{ $t("pos_data_vis.view_bounding_box") }}
              <v-icon
                :class="{
                  'text-disabled': !markerStore.showBoundingBox,
                  'text-red': markerStore.showBoundingBox,
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
              {{ $t("pos_data_vis.video_sync") }}
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

          <v-menu offset-x location="end" open-on-hover>
            <template v-slot:activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title>
                  {{ $t("pos_data_vis.view_kpis.title") }}
                  <v-icon class="ml-4 mb-1" size="small">mdi-chevron-right</v-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact">
              <v-list-item class="menu-item" @click="markerStore.viewSpaceControl">
                <v-list-item-title>
                  {{ $t("pos_data_vis.view_kpis.space_control") }}
                  <v-icon
                    :class="{
                      'text-disabled': !markerStore.showSpaceControl,
                      'text-red': markerStore.showSpaceControl,
                    }"
                    class="ml-4 mb-1"
                    size="small"
                  >
                    mdi-check
                  </v-icon>
                </v-list-item-title>
              </v-list-item>
              <v-list-item class="menu-item" @click="markerStore.viewEffectivePlayingSpace">
                <v-list-item-title>
                  {{ $t("pos_data_vis.view_kpis.eps") }}
                  <v-icon
                    :class="{
                      'text-disabled': !markerStore.showEffectivePlayingSpace,
                      'text-red': markerStore.showEffectivePlayingSpace,
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
        </v-list>
      </v-menu>

      <div class="time-code flex-grow-1 flex-shrink-0 ml-2">
        {{ getTimecode(sliderValue) }}
      </div>
    </v-row>

    <v-row>
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
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useCompAreaStore } from "@/stores/comp_area";
import { useMarkerStore } from "@/stores/marker";
import { getTimecode } from "@/plugins/time";
import { Delaunay } from "d3-delaunay";

const playerStore = usePlayerStore();
const compAreaStore = useCompAreaStore();
const markerStore = useMarkerStore();

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

const compAreaElement = ref(null);
const updateCompAreaSize = () => {
  nextTick(() => {
    if (compAreaElement.value) {
      const rect = compAreaElement.value.getBoundingClientRect();
      const size = {
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
      };

      compAreaStore.setCompAreaSize(size);
    }
  });
};

const handleResize = () => {
  updateCompAreaSize();
};

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
  if (!compAreaStore.compAreaSize || !markerStore.positions) {
    return [];
  }

  return markerStore.positions.map((framePositions) => {
    const teams = {};

    framePositions.forEach((position) => {
      if (!teams[position.team]) {
        teams[position.team] = [];
      }
      teams[position.team].push({
        top:
          (position.bbox_top + position.bbox_height) *
            (compAreaStore.compAreaSize.height * compAreaStore.currentSport.heightRel) +
          (compAreaStore.compAreaSize.top +
            ((1 - compAreaStore.currentSport.heightRel) / 2) * compAreaStore.compAreaSize.height),
        left:
          (position.bbox_left + position.bbox_width / 2) *
            (compAreaStore.compAreaSize.width * compAreaStore.currentSport.widthRel) +
          (compAreaStore.compAreaSize.left +
            ((1 - compAreaStore.currentSport.widthRel) / 2) * compAreaStore.compAreaSize.width),
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
    compAreaStore.compAreaSize.left +
      ((1 - compAreaStore.currentSport.widthRel) / 2) * compAreaStore.compAreaSize.width,
    compAreaStore.compAreaSize.top +
      ((1 - compAreaStore.currentSport.heightRel) / 2) * compAreaStore.compAreaSize.height,
    compAreaStore.compAreaSize.left +
      ((1 - compAreaStore.currentSport.widthRel) / 2) * compAreaStore.compAreaSize.width +
      compAreaStore.compAreaSize.width * compAreaStore.currentSport.widthRel,
    compAreaStore.compAreaSize.top +
      ((1 - compAreaStore.currentSport.heightRel) / 2) * compAreaStore.compAreaSize.height +
      compAreaStore.compAreaSize.height * compAreaStore.currentSport.heightRel,
  ]);

  return players
    .map((player, i) => {
      const polygon = voronoi.cellPolygon(i);
      return polygon ? { team: player.team, polygon } : null;
    })
    .filter((cell) => cell !== null);
};

const voronoiCells = computed(() => {
  if (!compAreaStore.compAreaSize || !markerStore.positions) {
    return [];
  }

  return markerStore.positions.map((framePositions) => {
    const allPlayers = framePositions.map((player) => ({
      top:
        (player.bbox_top + player.bbox_height) *
          compAreaStore.compAreaSize.height *
          compAreaStore.currentSport.heightRel +
        (compAreaStore.compAreaSize.top +
          ((1 - compAreaStore.currentSport.heightRel) / 2) * compAreaStore.compAreaSize.height),
      left:
        (player.bbox_left + player.bbox_width / 2) *
          compAreaStore.compAreaSize.width *
          compAreaStore.currentSport.widthRel +
        (compAreaStore.compAreaSize.left +
          ((1 - compAreaStore.currentSport.widthRel) / 2) * compAreaStore.compAreaSize.width),
      team: player.team,
    }));

    return computeVoronoi(allPlayers);
  });
});

onMounted(() => {
  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
  }, 500);
  updateCompAreaSize();
  window.addEventListener("resize", handleResize);
  window.addEventListener("scroll", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  window.removeEventListener("scroll", handleResize);
});
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
