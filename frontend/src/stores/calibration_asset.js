import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { useVideoStore } from "./video";
import { useTopViewStore } from "./top_view";
import { usePlayerStore } from "@/stores/player";

export const useCalibrationAssetStore = defineStore("calibration_asset", () => {
  const videoStore = useVideoStore();
  const topViewStore = useTopViewStore();
  const playerStore = usePlayerStore();

  const isLoading = ref(false);

  const marker = ref([
    {
      name: "Top-left",
      id: "1",
      active: false,
      compAreaCoordsRel: { x: 0, y: 0, z: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Top-right",
      id: "2",
      active: false,
      compAreaCoordsRel: { x: 0, y: 1, z: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Kick-off",
      id: "3",
      active: false,
      compAreaCoordsRel: { x: 0.5, y: 0.5, z: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Bottom-left",
      id: "4",
      active: false,
      compAreaCoordsRel: { x: 1, y: 0, z: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Bottom-right",
      id: "5",
      active: false,
      compAreaCoordsRel: { x: 1, y: 1, z: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
  ]);

  const isAddingReferenceMarker = ref(false);

  const filteredReferenceMarker = computed(() => {
    return marker.value.filter(
      (marker) => marker.compAreaCoordsRel.x !== null && marker.compAreaCoordsRel.y !== null
    );
  });

  const isAnyReferenceMarkerActive = computed(() => marker.value.some((marker) => marker.active));

  const toggleReferenceMarker = (event, id) => {
    event.stopPropagation();

    marker.value = marker.value.map((marker) => ({
      ...marker,
      active: marker.id === id ? !marker.active : false,
    }));
  };

  const addReferenceMarker = () => {
    if (!isAddingReferenceMarker.value) {
      isAddingReferenceMarker.value = true;

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

  const setReferenceMarker = (event) => {
    if (isAddingReferenceMarker.value) {
      const lastMarker = marker.value[marker.value.length - 1];
      if (lastMarker) {
        lastMarker.compAreaCoordsRel = {
          x:
            (event.clientX -
              (topViewStore.topViewSize.left +
                ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width)) /
            (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel),
          y:
            (event.clientY -
              (topViewStore.topViewSize.top +
                ((1 - topViewStore.currentSport.heightRel) / 2) *
                  topViewStore.topViewSize.height)) /
            (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel),
        };
      }

      isAddingReferenceMarker.value = false;
    }
  };

  const deleteReferenceMarker = (id) => {
    marker.value = marker.value.filter((m) => m.id !== id);
  };

  const showVideoMarker = ref(false);
  const hoveredVideoMarker = ref(null);

  const filteredVideoMarker = computed(() => {
    return marker.value.filter(
      (marker) => marker.videoCoordsRel.x !== null && marker.videoCoordsRel.y !== null
    );
  });

  const setVideoMarker = (event) => {
    const activeMarker = marker.value.find((marker) => marker.active);
    if (!activeMarker) return;

    activeMarker.videoCoordsRel = {
      x: (event.clientX - videoStore.videoSize.left) / videoStore.videoSize.width,
      y: (event.clientY - videoStore.videoSize.top) / videoStore.videoSize.height,
    };

    activeMarker.active = false;
  };

  const toggleVideoMarker = () => {
    showVideoMarker.value = !showVideoMarker.value;
  };

  const calibrationAssetsList = ref({});

  const loadCalibrationAssetsList = async () => {
    try {
      const params = {};
      if (playerStore.videoId) {
        params.video_id = playerStore.videoId;
      }
      const res = await axios.get(`${config.API_LOCATION}/calibration_assets/list`, { params });
      if (res.data.status === "ok") {
        updateStore(res.data.entries);
        calibrationAssetsList.value = res.data.entries;
        return res.data.entries;
      }
    } catch (error) {
      console.error("Failed to list calibration assets:", error);
    }
  };

  const loadCalibrationAsset = (id) => {
    const calibrationAsset = calibrationAssetsList.value.find((asset) => asset.id === id);
    if (calibrationAsset) {
      marker.value = calibrationAsset.marker_data;
      topViewStore.currentSport = topViewStore.sports.find(
        (sport) => sport.title === calibrationAsset.template
      );
    }
  };

  const createCalibrationAsset = async (name, template) => {
    if (isLoading.value || !name) return;
    isLoading.value = true;
    const params = {
      name,
      template,
      marker_data: [...marker.value],
      video_id: playerStore.videoId,
    };
    try {
      const res = await axios.post(`${config.API_LOCATION}/calibration_assets/create`, params);
      if (res.data.status === "ok") {
        addToStore([res.data.entry]);
        loadCalibrationAssetsList();
        return res.data.entry.id;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const updateCalibrationAsset = async ({ name, template }) => {
    if (isLoading.value || !name || !template) return;
    isLoading.value = true;
    const params = {
      name,
      template,
      marker_data: [...marker.value],
    };
    try {
      const res = await axios.post(`${config.API_LOCATION}/calibration_assets/update`, params);
      if (res.data.status === "ok") {
        updateInStore([res.data.entry]);
        loadCalibrationAssetsList();
        return res.data.entry;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const deleteCalibrationAsset = async (id) => {
    if (isLoading.value || !id) return;
    isLoading.value = true;
    const params = { id };
    try {
      const res = await axios.post(`${config.API_LOCATION}/calibration_assets/delete`, params);
      if (res.data.status === "ok") {
        delete calibrationAssetsList.value[id];
        loadCalibrationAssetsList();
      }
    } finally {
      isLoading.value = false;
    }
  };

  const updateStore = (newCalibrationAsset) => {
    newCalibrationAsset.forEach((e) => {
      if (!(e.id in calibrationAssetsList)) {
        calibrationAssetsList[e.id] = e;
      }
    });
  };

  const addToStore = (newCalibrationAsset) => {
    newCalibrationAsset.forEach((e) => {
      calibrationAssetsList[e.id] = e;
    });
  };

  const updateInStore = (newCalibrationAsset) => {
    newCalibrationAsset.forEach((e) => {
      calibrationAssetsList[e.id] = e;
    });
  };

  return {
    marker,
    marker,
    filteredReferenceMarker,
    filteredVideoMarker,
    toggleReferenceMarker,
    isAnyReferenceMarkerActive,
    isAddingReferenceMarker,
    addReferenceMarker,
    setReferenceMarker,
    deleteReferenceMarker,
    setVideoMarker,
    showVideoMarker,
    toggleVideoMarker,
    hoveredVideoMarker,
    calibrationAssetsList,
    loadCalibrationAsset,
    loadCalibrationAssetsList,
    createCalibrationAsset,
    updateCalibrationAsset,
    deleteCalibrationAsset,
  };
});
