<template>
  <v-container class="d-flex flex-column">
    <div v-if="markerStore.isAnyMarkerActive" ref="overlay" class="overlay" @click="markerStore.setReferenceMarker"></div>

    <v-row ref="visualizerContainer" class="visualizer-container mt-n1">
      <div class="mx-4" @click="handleMarkerClick">
        <img
          ref="compAreaElement"
          class="visualizer-image"
          :src="currentSport.pitchImage"
        />

        <v-btn
          v-for="m in marker"
          :key="m.id"
          :color="(m.active || markerStore.hoveredReferenceMarker === m.id) ? 'red' : 'grey'"
          icon="mdi-circle"
          variant="plain"
          @click="(event) => markerStore.toggleMarker(event, m.id)"
          :style="{
            top: (m.compAreaCoordsRel.y * compAreaStore.compAreaSize.height) + 'px',
            left: (m.compAreaCoordsRel.x * compAreaStore.compAreaSize.width) + 'px'
          }"
          style="position: absolute;  z-index: 10; transform: translate(-8%, -25%);"
        />

        <v-btn
          v-for="m in marker"
          v-show="showDeleteButton"
          :key="'delete-' + m.id"
          color="red"
          icon="mdi-close"
          variant="text"
          @click="markerStore.deleteMarker(m.id)"
          :style="{
            top: (m.compAreaCoordsRel.y * compAreaStore.compAreaSize.height) + 'px',
            left: (m.compAreaCoordsRel.x * compAreaStore.compAreaSize.width) + 'px',
          }"
          style="position: absolute; z-index: 11; transform: translate(-8%, -25%) scale(0.8);"
        />
      </div>
    </v-row>

    <v-row class="video-control mt-7 mx-1">
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

      <v-spacer></v-spacer>

      <v-btn 
        size="small" 
        @click="markerStore.viewReferenceMarker" 
        :color="markerStore.showReferenceMarker ? 'primary' : 'white'"
      >
        View Ref-Marker
      </v-btn>

      <v-btn 
        size="small" 
        @click="markerStore.addMarker"
        :color="markerStore.isAddingMarker ? 'primary' : 'white'"
      >
        Add Marker
      </v-btn>

      <v-btn 
        size="small" 
        @click="showDeleteButton = !showDeleteButton"
        :color="showDeleteButton ? 'primary' : 'white'"
      >
        Delete Marker
      </v-btn>
    </v-row>

    <v-row> 
        <v-list class="ma-2">
          <v-list-item v-for="m in marker" :key="m.id">
            <v-list-item-content>
              <v-list-item-title>
                {{ m.name }}: 
                <span v-if="m.videoCoordsRel.x !== null && m.videoCoordsRel.y !== null && m.videoCoordsRel.z !== null">
                  (X: {{ m.videoCoordsRel.x }} px, Y: {{ m.videoCoordsRel.y }} px, Z: {{ m.videoCoordsRel.z }} px)
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
import { useVideoStore } from "@/stores/video";
import { useCompAreaStore } from "@/stores/comp_area";
import { useMarkerStore } from "@/stores/marker";

export default {
  emits: ["resize"],
  setup(_, { emit }) {
    const videoStore = useVideoStore();
    const compAreaStore = useCompAreaStore();
    const markerStore = useMarkerStore();

    const compAreaElement = ref(null);
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
  
    const marker = computed(() => markerStore.marker);

    const showDeleteButton = ref(false);

    const overlay = ref(null);
 
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
          emit("resize", size);
        }
      });
    };

    const handleResize = () => {
      updateCompAreaSize();
    };

    const handleClickOverlay = (event) => {
      const activeMarker = marker.value.find(m => m.active);
      if (!activeMarker || !overlay.value) return;
      if (!overlay.value.contains(event.target)) return;
    };

    const handleMarkerClick = (event) => {
      if (!markerStore.isAddingMarker || !compAreaElement.value) return;

      const clickX = (event.clientX - compAreaStore.compAreaSize.left) / compAreaStore.compAreaSize.width;
      const clickY = (event.clientY - compAreaStore.compAreaSize.top) / compAreaStore.compAreaSize.height;

      markerStore.setMarkerPosition(clickX, clickY);
    };

    // const addMarkerAtClick = (event) => {
    //   if (!compAreaElement.value) return;
      
    //   const clickX = (event.clientX - compAreaStore.compAreaSize.left) / compAreaStore.compAreaSize.width;
    //   const clickY = (event.clientY - compAreaStore.compAreaSize.top) / compAreaStore.compAreaSize.height;

    //   markerStore.addMarker(clickX, clickY);
    // };

    onMounted(() => {
      updateCompAreaSize();
      window.addEventListener('click', handleClickOverlay);
      window.addEventListener("resize", handleResize);
    });

    onUnmounted(() => {
      window.removeEventListener('click', handleClickOverlay);
      window.removeEventListener("resize", handleResize);
    });

    return {
      videoStore,
      compAreaStore,
      markerStore,
      currentSport,
      sports,
      onSportChange,
      marker,
      compAreaElement,
      updateCompAreaSize,
      handleMarkerClick,
      showDeleteButton
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

.marker-position {
  position: fixed;
  width: 10px;
  height: 10px;
  background-color: red;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
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
  z-index: 5;
  pointer-events: auto;
  border: 4px solid red;
}
</style>