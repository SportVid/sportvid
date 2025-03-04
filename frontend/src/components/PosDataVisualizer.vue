<template>
  <v-container class="d-flex flex-column">
    <v-row class="mx-2 mt-1">
      <img
        ref="compAreaElement"
        class="visualizer-image"
        :src="currentSport.pitchImage"
        @load="updateCompAreaSize"
      />

      <div
        v-for="(position, index) in markerStore.positions[sliderValue]"
        :key="index"
        class="data-point-position"
        :style="{
          top:
            (position.bbox_top + position.bbox_height) * compAreaStore.compAreaSize.height +
            compAreaStore.compAreaSize.top +
            'px',
          left:
            (position.bbox_left + position.bbox_width / 2) * compAreaStore.compAreaSize.width +
            compAreaStore.compAreaSize.left +
            'px',
          backgroundColor: `${position.team}`,
        }"
      />
    </v-row>

    <v-row class="video-control mt-8 mx-1 mb-n1">
      <v-menu offset-y top>
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ currentSport.title }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item v-for="(item, index) in sports" :key="index" class="sport-item">
            <v-list-item-title v-on:click="onSportChange(index)">
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-btn
        size="small"
        @click="markerStore.viewBoundingBox"
        :color="markerStore.showBoundingBox ? 'primary' : 'white'"
      >
        {{ $t("pos_data_vis.view_bounding_box") }}
      </v-btn>

      <v-btn @click="playerStore.toggleSliderSync" size="small">
        <v-icon v-if="playerStore.isSynced"> mdi-link-off</v-icon>
        <v-icon v-else> mdi-link</v-icon>
      </v-btn>

      <div class="time-code flex-grow-1 flex-shrink-0 ml-2">
        {{ getTimecode(sliderValue) }}
      </div>
    </v-row>

    <v-row class="mx-0">
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

<script>
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useCompAreaStore } from "@/stores/comp_area";
import { useMarkerStore } from "@/stores/marker";
import { getTimecode } from "@/plugins/time";

export default {
  setup() {
    const playerStore = usePlayerStore();
    const compAreaStore = useCompAreaStore();
    const markerStore = useMarkerStore();

    const currentSport = ref({
      title: "Soccer",
      pitchImage: require("../assets/pitch_soccer.png"),
    });
    const sports = [
      { title: "Soccer", pitchImage: require("../assets/pitch_soccer.png") },
      { title: "Handball", pitchImage: require("../assets/pitch_handball.png") },
      { title: "Basketball", pitchImage: require("../assets/pitch_basketball.png") },
      { title: "Climbing", pitchImage: require("../assets/pitch_climbing.png") },
    ];
    const onSportChange = (idx) => {
      currentSport.value = sports[idx];
    };

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

    return {
      playerStore,
      compAreaStore,
      markerStore,
      currentSport,
      sports,
      onSportChange,
      currentFrame,
      updateFrame,
      currentTime,
      sliderValue,
      getTimecode,
      compAreaElement,
    };
  },
};
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

.sport-item {
  cursor: pointer;
}

.sport-item:hover {
  background-color: #f0f0f0;
}
</style>
