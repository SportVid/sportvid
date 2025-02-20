<template>
  <v-container class="d-flex flex-column">
    <div v-if="isAnyButtonActive" class="overlay"></div>

    <v-row ref="visualizerContainer" class="visualizer-container mt-n1">
      <img
        class="visualizer-image"
        :src="currentSport.pitchImage"
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
          <v-list-item 
            v-for="(item, index) in sports" 
            :key="index"
            class="sport-item"
          >
            <v-list-item-title v-on:click="onSportChange(index)">
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
      
      <!-- <v-btn
        v-for="button in buttons"
        :key="button.id"
        :color="button.active ? 'red' : 'grey'"
        dark
        icon="mdi-circle-medium"
        variant="icon"
        @click="(event) => toggleButton(event, button.id)"
        class="custom-button"
        :style="{ top: button.top + 'px', right: button.right + 'px' }"
      >
      </v-btn> -->
      <v-btn
        v-for="button in buttons"
        :key="button.id"
        :color="button.active ? 'red' : 'grey'"
        
        @click="(event) => toggleButton(event, button.id)"
        class="custom-button"
        :style="{ 
          top: button.top + 'px', 
          right: button.right + 'px',
        }"
        style="position: absolute; z-index: 10;"
        fab
        height=35
        rounded="xl"
        size="x-small"
      >
        {{ button.id }}
      </v-btn>
    </v-row>
    <v-row> 
        <v-list class="ma-2">
          <v-list-item v-for="button in buttons" :key="button.id">
            <v-list-item-content>
              <v-list-item-title>
                {{ button.name }} ({{ button.id }}): 
                <span v-if="button.coords.x !== null && button.coords.y !== null">
                  (X: {{ button.coords.x }} px, Y: {{ button.coords.y }} px, Z: {{ button.coords.z }} px)
                </span>
                <span v-else> Noch nicht gesetzt </span>
              </v-list-item-title>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </v-row>
  </v-container>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { usePlayerStore } from "@/stores/player";
import { getTimecode } from "@/plugins/time";

export default {
  setup() {
    const playerStore = usePlayerStore();

    const currentSport = ref({ title: 'Soccer', pitchImage: require('../assets/pitch_soccer.png') });
    const sports = [
      { title: 'Soccer', pitchImage: require('../assets/pitch_soccer.png') },
      { title: 'Handball', pitchImage: require('../assets/pitch_handball.png') },
      { title: 'Basketball', pitchImage: require('../assets/pitch_basketball.png') },
      { title: 'Climbing', pitchImage: require('../assets/pitch_climbing.png') },
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
    }
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
      }
    });

    const buttons = ref([
      { 
        name: 'Oben links', 
        id: '1', 
        top: -12, 
        right: 682, 
        active: false, 
        coords: { x: null, y: null, z: null } 
      },
      { 
        name: 'Oben rechts', 
        id: '2', 
        top: -12, 
        right: -20, 
        active: false, 
        coords: { x: null, y: null, z: null } 
      },
      { 
        name: 'Mittelpunkt', 
        id: '3', 
        top: 217, 
        right: 332, 
        active: false, 
        coords: { x: null, y: null, z: null } 
      },
      { 
        name: 'Unten links', 
        id: '4', 
        top: 446, 
        right: 682, 
        active: false, 
        coords: { x: null, y: null, z: null } 
      },
      { 
        name: 'Unten rechts', 
        id: '5', 
        top: 446, 
        right: -20, 
        active: false, 
        coords: { x: null, y: null, z: null } 
      },
    ]);

    const toggleButton = (event, id) => {
      event.stopPropagation();
      
      buttons.value = buttons.value.map(button => ({
        ...button,
        active: button.id === id ? !button.active : false
      }));
    };

    const handleClickOutsideButton = (event) => {
      const activeButton = buttons.value.find(button => button.active);
      if (!activeButton) return;

      activeButton.coords = { x: event.clientX, y: event.clientY };
      activeButton.active = false;
    };

    const isAnyButtonActive = computed(() => buttons.value.some(button => button.active));

    onMounted(() => {
      window.addEventListener('click', handleClickOutsideButton);
    });

    onUnmounted(() => {
      window.removeEventListener('click', handleClickOutsideButton);
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
      toggleButton,
      buttons,
      isAnyButtonActive,
    }
  }
}
  
</script>

<style>
.visualizer-container {
  height: 100%;
  justify-content: center
}

.visualizer-image {
  max-width: 100%;
  max-height: 100%;
}

.position-marker {
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
  background-color: #f0f0f0;
}

.overlay {
  position: fixed;
  top: 64px;
  left: 0;
  width: 100%;
  height: calc(100vh - 64px);
  background: rgba(255, 255, 255, 0.5);
  z-index: 1000;
  pointer-events: auto;
  border: 4px solid red;
}
</style>