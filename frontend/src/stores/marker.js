import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useVideoStore } from "./video";
import { useCompAreaStore } from "./comp_area";

export const useMarkerStore = defineStore("marker", () => {
  const videoStore = useVideoStore();
  const compAreaStore = useCompAreaStore();

  const showReferenceMarker = ref(true);
  const hoveredReferenceMarker = ref(null);
  const isAddingMarker = ref(false);
  const showBoundingBox = ref(false);

  const marker = ref([
    {
      name: "Top-left",
      id: "1",
      active: false,
      compAreaCoordsRel: { x: 0, y: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Top-right",
      id: "2",
      active: false,
      compAreaCoordsRel: { x: 0, y: 1 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Kick-off",
      id: "3",
      active: false,
      compAreaCoordsRel: { x: 0.5, y: 0.5 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Bottom-left",
      id: "4",
      active: false,
      compAreaCoordsRel: { x: 1, y: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Bottom-right",
      id: "5",
      active: false,
      compAreaCoordsRel: { x: 1, y: 1 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
  ]);

  const filteredMarker = computed(() => {
    return marker.value.filter(
      (marker) => marker.compAreaCoordsRel.x !== null && marker.compAreaCoordsRel.y !== null
    );
  });

  const filteredReferenceMarker = computed(() => {
    return marker.value.filter(
      (marker) => marker.videoCoordsRel.x !== null && marker.videoCoordsRel.y !== null
    );
  });

  const isAnyMarkerActive = computed(() => marker.value.some((marker) => marker.active));

  const toggleMarker = (event, id) => {
    event.stopPropagation();

    marker.value = marker.value.map((marker) => ({
      ...marker,
      active: marker.id === id ? !marker.active : false,
    }));
  };

  const addMarker = () => {
    if (!isAddingMarker.value) {
      isAddingMarker.value = true;

      const customMarkerCount = marker.value.filter((m) =>
        m.name.startsWith("Custom-marker")
      ).length;
      const newMarker = {
        name: `Custom-marker-${customMarkerCount + 1}`,
        id: marker.value.length + 1,
        active: false,
        compAreaCoordsRel: { x: null, y: null, z: null },
        videoCoordsRel: { x: null, y: null, z: null },
      };

      marker.value.push(newMarker);
    }
  };

  const setMarker = (event) => {
    if (isAddingMarker.value) {
      const lastMarker = marker.value[marker.value.length - 1];
      if (lastMarker) {
        lastMarker.compAreaCoordsRel = {
          x: (event.clientX - compAreaStore.compAreaSize.left) / compAreaStore.compAreaSize.width,
          y: (event.clientY - compAreaStore.compAreaSize.top) / compAreaStore.compAreaSize.height,
        };
      }

      isAddingMarker.value = false;
    }
  };

  const deleteMarker = (id) => {
    marker.value = marker.value.filter((m) => m.id !== id);
  };

  const setReferenceMarker = (event) => {
    const activeMarker = marker.value.find((marker) => marker.active);
    if (!activeMarker) return;

    activeMarker.videoCoordsRel = {
      x: (event.clientX - videoStore.videoSize.left) / videoStore.videoSize.width,
      y: (event.clientY - videoStore.videoSize.top) / videoStore.videoSize.height,
    };

    activeMarker.active = false;
  };

  const viewReferenceMarker = () => {
    showReferenceMarker.value = !showReferenceMarker.value;
  };

  const viewBoundingBox = () => {
    showBoundingBox.value = !showBoundingBox.value;
  };

  const positions = ref(
    Array.from({ length: 100 }, (_, frameIndex) =>
      Array.from({ length: 3 }, (_, pointIndex) => ({
        bbox_top: (frameIndex * 0.5 + pointIndex * 2) / (100 * 0.5 + 2),
        bbox_left: (frameIndex * 0.5 + pointIndex * 2) / (100 * 0.5 + 2),
        bbox_width: 0.05,
        bbox_height: 0.1,
        team: "blue",
      }))
    )
  );

  return {
    marker,
    filteredMarker,
    filteredReferenceMarker,
    toggleMarker,
    isAnyMarkerActive,
    isAddingMarker,
    addMarker,
    setMarker,
    deleteMarker,
    setReferenceMarker,
    showReferenceMarker,
    viewReferenceMarker,
    hoveredReferenceMarker,
    showBoundingBox,
    viewBoundingBox,
    positions,
  };
});
