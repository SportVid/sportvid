<template>
  <v-container class="d-flex flex-column">
    <div
      v-if="markerStore.isAnyMarkerActive"
      ref="overlayReferenceMarker"
      class="overlay-reference-marker"
      @click="markerStore.setReferenceMarker"
    />

    <v-row class="mx-2 mt-1">
      <div
        v-if="markerStore.isAddingMarker"
        ref="overlayMarker"
        class="overlay-marker"
        @click="markerStore.setMarker"
        :style="{
          top: compAreaStore.compAreaSize.top + 'px',
          left: compAreaStore.compAreaSize.left + 'px',
          width: compAreaStore.compAreaSize.width + 'px',
          height: compAreaStore.compAreaSize.height + 'px',
        }"
      />

      <img
        ref="compAreaElement"
        class="visualizer-image"
        :src="currentSport.pitchImage"
        @load="updateCompAreaSize"
      />

      <v-btn
        v-for="m in filteredMarker"
        :key="m.id"
        :disabled="markerStore.isAddingMarker"
        :color="m.active || markerStore.hoveredReferenceMarker === m.id ? 'red' : 'grey'"
        icon="mdi-circle"
        variant="plain"
        density="compact"
        @click="(event) => markerStore.toggleMarker(event, m.id)"
        :style="{
          top:
            m.compAreaCoordsRel.y * compAreaStore.compAreaSize.height +
            compAreaStore.compAreaSize.top +
            'px',
          left:
            m.compAreaCoordsRel.x * compAreaStore.compAreaSize.width +
            compAreaStore.compAreaSize.left +
            'px',
        }"
        class="marker-position"
      />

      <v-btn
        v-for="m in filteredMarker"
        v-show="showDeleteButton"
        :key="'delete-' + m.id"
        color="red"
        icon="mdi-close"
        variant="plain"
        density="compact"
        @click="markerStore.deleteMarker(m.id)"
        :style="{
          top:
            m.compAreaCoordsRel.y * compAreaStore.compAreaSize.height +
            compAreaStore.compAreaSize.top +
            'px',
          left:
            m.compAreaCoordsRel.x * compAreaStore.compAreaSize.width +
            compAreaStore.compAreaSize.left +
            'px',
        }"
        class="delete-marker-position"
      />
    </v-row>

    <v-row class="video-control mt-10 mx-1 mb-2">
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

      <v-spacer />

      <v-btn
        size="small"
        @click="markerStore.viewReferenceMarker"
        :color="markerStore.showReferenceMarker ? 'primary' : 'white'"
      >
        {{ $t("annotation_vis.view_ref_marker") }}
      </v-btn>

      <v-btn
        size="small"
        @click="handleAddMarker"
        :color="markerStore.isAddingMarker ? 'primary' : 'white'"
      >
        {{ $t("annotation_vis.add_marker") }}
      </v-btn>

      <v-btn
        size="small"
        @click="showDeleteButton = !showDeleteButton"
        :color="showDeleteButton ? 'primary' : 'white'"
      >
        {{ $t("annotation_vis.delete_marker") }}
      </v-btn>
    </v-row>

    <!-- <v-row>
      <v-list class="ma-2">
        <v-list-item v-for="m in filteredMarker" :key="m.id">
          <v-list-item-content>
            <v-list-item-title>
              {{ m.name }}:
              <span v-if="m.videoCoordsRel.x !== null && m.videoCoordsRel.y !== null !== null">
                  (X: {{ m.videoCoordsRel.x }} px, Y: {{ m.videoCoordsRel.y }} px, Z: {{ m.videoCoordsRel.z }} px)
                </span>
              <span
                v-if="m.compAreaCoordsRel.x !== null && (m.compAreaCoordsRel.y !== null) !== null"
              >
                (X: {{ m.compAreaCoordsRel.x }} px, Y: {{ m.compAreaCoordsRel.y }} px, Z:
                {{ m.compAreaCoordsRel.z }} px)
              </span>
              <span v-else> Noch nicht gesetzt </span>
            </v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-row> -->
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { useVideoStore } from "@/stores/video";
import { useCompAreaStore } from "@/stores/comp_area";
import { useMarkerStore } from "@/stores/marker";

const videoStore = useVideoStore();
const compAreaStore = useCompAreaStore();
const markerStore = useMarkerStore();

const compAreaElement = ref(null);

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

const marker = computed(() => markerStore.marker);
const filteredMarker = computed(() => markerStore.filteredMarker);

const showDeleteButton = ref(false);

const overlayMarker = ref(null);
const overlayReferenceMarker = ref(null);

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

const handleClickOverlayReferenceMarker = (event) => {
  const activeMarker = marker.value.find((m) => m.active);
  if (!activeMarker || !overlayReferenceMarker.value) return;
  if (!overlayReferenceMarker.value.contains(event.target)) return;
};

const handleClickOverlayMarker = (event) => {
  if (!markerStore.isAddingMarker || !overlayMarker.value) return;
  if (!overlayMarker.value.contains(event.target)) return;
};

const handleAddMarker = () => {
  if (showDeleteButton.value) {
    showDeleteButton.value = false;
    nextTick(() => {
      markerStore.addMarker();
    });
  } else {
    markerStore.addMarker();
  }
};

onMounted(() => {
  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
  }, 500);
  updateCompAreaSize();
  window.addEventListener("click", handleClickOverlayReferenceMarker);
  window.addEventListener("click", handleClickOverlayMarker);
  window.addEventListener("resize", handleResize);
  window.addEventListener("scroll", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("click", handleClickOverlayReferenceMarker);
  window.removeEventListener("click", handleClickOverlayMarker);
  window.removeEventListener("resize", handleResize);
  window.removeEventListener("scroll", handleResize);
});
</script>

<style>
.visualizer-image {
  max-width: 100%;
  max-height: 100%;
}

.marker-position {
  position: fixed;
  transform: translate(-50%, -50%);
  z-index: 1000;
}

.delete-marker-position {
  position: fixed;
  transform: translate(-50%, -50%);
  z-index: 1001;
}

.delete-marker-position .v-icon {
  transform: scale(0.7);
}

.delete-marker-position:hover {
  border: 1px red solid;
}

.video-control {
  gap: 5px;
}

.sport-item {
  cursor: pointer;
}

.sport-item:hover {
  background-color: #f0f0f0;
}

.overlay-reference-marker {
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

.overlay-marker {
  position: fixed;
  background: rgba(255, 255, 255, 0.5);
  z-index: 5;
  border: 4px solid red;
}
</style>
