import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useVideoStore } from "./video";

export const useMarkerStore = defineStore("marker", () => {
  const videoStore = useVideoStore();

  const showReferenceMarker = ref(true);
  const hoveredReferenceMarker = ref(null);
  const isAddingMarker = ref(false);
  
  const marker = ref([
    { 
      name: 'Top-left', 
      id: '1',
      active: false, 
      compAreaCoordsRel: { x: 0, y: 0 },
      videoCoordsRel: { x: null, y: null, z: null }
    },
    { 
      name: 'Top-right', 
      id: '2',
      active: false, 
      compAreaCoordsRel: { x: 0, y: 1 },
      videoCoordsRel: { x: null, y: null, z: null }
    },
    { 
      name: 'Kick-off', 
      id: '3',
      active: false, 
      compAreaCoordsRel: { x: 0.5, y: 0.5 },
      videoCoordsRel: { x: null, y: null, z: null }
    },
    { 
      name: 'Bottom-left', 
      id: '4',
      active: false, 
      compAreaCoordsRel: { x: 1, y: 0 },
      videoCoordsRel: { x: null, y: null, z: null } 
    },
    { 
      name: 'Bottom-right', 
      id: '5',
      active: false, 
      compAreaCoordsRel: { x: 1, y: 1 },
      videoCoordsRel: { x: null, y: null, z: null }
    },
  ]);

  const filteredMarker = computed(() => {
    return marker.value.filter(
      marker => marker.videoCoordsRel.x !== null && marker.videoCoordsRel.y !== null
    );
  });

  const isAnyMarkerActive = computed(() => marker.value.some(marker => marker.active)); 

  const toggleMarker = (event, id) => {
    event.stopPropagation();
    
    marker.value = marker.value.map(marker => ({
      ...marker,
      active: marker.id === id ? !marker.active : false
    }));
  };

  const addMarker = () => {
    if (!isAddingMarker.value) {
      isAddingMarker.value = true;

      const newMarker = {
        id: marker.value.length + 1,
        active: false,
        compAreaCoordsRel: { x: null, y: null},
        videoCoordsRel: { x: null, y: null, z: null }
      };
    
      marker.value.push(newMarker);
    }
  };

  const setMarkerPosition = (clickX, clickY) => {
    if (isAddingMarker.value) {
      const lastMarker = marker.value[marker.value.length - 1];
      if (lastMarker) {
        lastMarker.compAreaCoordsRel = { x: clickX, y: clickY };
      }
      isAddingMarker.value = false;
    }
  };

  const deleteMarker = (id) => {
    marker.value = marker.value.filter(m => m.id !== id);
  };

  const setReferenceMarker = (event) => {
    const activeMarker = marker.value.find(marker => marker.active);
    if (!activeMarker) return;

    activeMarker.videoCoordsRel = {
      x: (event.clientX - videoStore.videoSize.left) / videoStore.videoSize.width, 
      y: (event.clientY - videoStore.videoSize.top) / videoStore.videoSize.height
    };

    activeMarker.active = false;
  };

  const viewReferenceMarker = () => {
    showReferenceMarker.value = !showReferenceMarker.value;
  };

  return {
    marker,
    filteredMarker,
    toggleMarker,
    isAnyMarkerActive,
    isAddingMarker,
    addMarker,
    setMarkerPosition,
    deleteMarker,
    setReferenceMarker,
    showReferenceMarker,
    viewReferenceMarker,
    hoveredReferenceMarker
  }
});