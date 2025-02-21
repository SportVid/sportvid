<template>
  <v-container class="d-flex flex-column">
    <div v-if="isAnyMarkerActive" class="overlay"></div>

    <v-row ref="visualizerContainer" class="visualizer-container mt-n1">
      <div class="mx-4">
        <img
          ref="pitchImage"
          class="visualizer-image"
          :src="currentSport.pitchImage"
          @load="setMarkerPosition"
        />

        <v-btn
          v-for="marker in referenceMarker"
          :key="marker.id"
          :color="marker.active ? 'red' : 'grey'"
          icon="mdi-circle"
          variant="plain"
          @click="(event) => toggleMarker(event, marker.id)"
          :style="markerPosition[marker.id]"
          style="position: absolute; z-index: 10; height: 15px; width: 15px;"
        >
        </v-btn>
      </div>
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

      <v-btn size="small" @click="viewMarker">
        View Marker
      </v-btn>

      <!-- <div
        v-for="marker in referenceMarker"
        v-if="showMarker"
        :key="marker.id"
        class="position-marker"
        :style="getMarkerPosition(marker)"
      ></div> -->
    </v-row>

    <v-row> 
        <v-list class="ma-2">
          <v-list-item v-for="marker in referenceMarker" :key="marker.id">
            <v-list-item-content>
              <v-list-item-title>
                {{ marker.name }}: 
                <span v-if="marker.videoCoords.x !== null && marker.videoCoords.y !== null && marker.videoCoords.z !== null">
                  (X: {{ marker.videoCoords.x }} px, Y: {{ marker.videoCoords.y }} px, Z: {{ marker.videoCoords.z }} px)
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
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { usePlayerStore } from "@/stores/player";

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

    const pitchImage = ref(null);
    const markerPosition = ref({ top: null, left: null });
    const referenceMarker = ref([
      { 
        name: 'Top-left', 
        id: '1',
        active: false, 
        compAreaCoords: { top: 0, left: 0 },
        videoCoords: { x: null, y: null, z: null } 
      },
      { 
        name: 'Top-right', 
        id: '2',
        active: false, 
        compAreaCoords: { top: 0, left: 1 },
        videoCoords: { x: null, y: null, z: null } 
      },
      { 
        name: 'Kick-off', 
        id: '3',
        active: false, 
        compAreaCoords: { top: 0.5, left: 0.5 },
        videoCoords: { x: null, y: null, z: null } 
      },
      { 
        name: 'Bottom-left', 
        id: '4',
        active: false, 
        compAreaCoords: { top: 1, left: 0 },
        videoCoords: { x: null, y: null, z: null } 
      },
      { 
        name: 'Bottom-right', 
        id: '5',
        active: false, 
        compAreaCoords: { top: 1, left: 1 },
        videoCoords: { x: null, y: null, z: null } 
      },
    ]);

    const toggleMarker = (event, id) => {
      event.stopPropagation();
      
      referenceMarker.value = referenceMarker.value.map(marker => ({
        ...marker,
        active: marker.id === id ? !marker.active : false
      }));
    };

    const handleClickOutsideMarker = (event) => {
      const activeMarker = referenceMarker.value.find(marker => marker.active);
      if (!activeMarker) return;

      activeMarker.videoCoords = { x: event.clientX, y: event.clientY };
      activeMarker.active = false;
    };

    const setMarkerPosition = () => {
      nextTick(() => {
        if (pitchImage.value) {
          const rect = pitchImage.value.getBoundingClientRect();
          markerPosition.value = referenceMarker.value.reduce((acc, marker) => {
            acc[marker.id] = {
              top: `${marker.compAreaCoords.top * rect.height}px`,
              left: `${marker.compAreaCoords.left * rect.width}px`,
            };
            return acc;
          }, {});
        }
      });
    };
    const handleResize = () => {
      setMarkerPosition();
    };

    const isAnyMarkerActive = computed(() => referenceMarker.value.some(marker => marker.active));

    const showMarker = ref(false);
    const viewMarker = () => {
      showMarker.value = !showMarker.value;
    };

    onMounted(() => {
      window.addEventListener("resize", handleResize);
      window.addEventListener('click', handleClickOutsideMarker);
      setMarkerPosition();
    });

    onUnmounted(() => {
      window.removeEventListener('click', handleClickOutsideMarker);
      window.removeEventListener("resize", handleResize);
    });

    return {
      playerStore,
      currentSport,
      sports,
      onSportChange,
      toggleMarker,
      referenceMarker,
      isAnyMarkerActive,
      viewMarker,
      showMarker,
      pitchImage,
      setMarkerPosition,
      markerPosition
    }
  }
}
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