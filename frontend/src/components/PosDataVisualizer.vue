<template>
  <v-container class="d-flex flex-column">
    <v-row ref="visualizerContainer" class="visualizer-container mt-n1">
      <img class="visualizer-image" :src="currentSport.pitchImage" />

      <div
        v-for="(position, index) in positions[sliderValue]"
        :key="index"
        class="data-point-position"
        :style="{
          top: `${position.y}%`,
          left: `${position.x}%`,
        }"
      />
    </v-row>

    <v-row class="video-control mt-6">
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

      <v-btn @click="toggleSliderSync" size="small">
        <v-icon v-if="playerStore.isSynced"> mdi-link-off</v-icon>
        <v-icon v-else> mdi-link</v-icon>
      </v-btn>

      <div class="time-code flex-grow-1 flex-shrink-0 ml-2">
        {{ getTimecode(sliderValue) }}
      </div>
    </v-row>

    <v-row class="mt-4">
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
import { ref, computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { getTimecode } from "@/plugins/time";

export default {
  setup() {
    const playerStore = usePlayerStore();

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

    const positions = ref(
      Array.from({ length: 100 }, (_, frameIndex) =>
        Array.from({ length: 3 }, (_, pointIndex) => ({
          x: 20 + frameIndex * 0.5 + pointIndex * 2,
          y: 20 + frameIndex * 0.5 + pointIndex * 2,
        }))
      )
    );

    const currentFrame = ref(0);
    const updateFrame = (newIndex) => {
      currentFrame.value = newIndex;
    };
    const toggleSliderSync = () => {
      playerStore.isSynced = !playerStore.isSynced;
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

    return {
      playerStore,
      currentSport,
      sports,
      onSportChange,
      positions,
      currentFrame,
      updateFrame,
      toggleSliderSync,
      currentTime,
      sliderValue,
      getTimecode,
    };
  },
};
</script>

<style>
.visualizer-container {
  height: 100%;
  justify-content: center;
}

.visualizer-image {
  max-width: 100%;
  max-height: 100%;
}

.data-point-position {
  position: absolute;
  width: 10px;
  height: 10px;
  background-color: red;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
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
  background-color: #f0f0f0; /* Markiere das Element bei Hover */
}
</style>
