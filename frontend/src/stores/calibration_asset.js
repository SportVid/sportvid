import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { inv } from "mathjs";
import { useVideoStore } from "./video";
import { useTopViewStore } from "./top_view";
import { usePlayerStore } from "@/stores/player";

export const useCalibrationAssetStore = defineStore("calibration_asset", () => {
  const videoStore = useVideoStore();
  const topViewStore = useTopViewStore();
  const playerStore = usePlayerStore();

  const isLoading = ref(false);

  const marker = ref([]);
  const markerTemplate = ref([
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

  const allMarkerValid = computed(() =>
    marker.value.every((m) => m.videoCoordsRel.x !== null && m.videoCoordsRel.y !== null)
  );

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
  const calibrationAssetId = ref(null);
  const createCalibrationAsset = (template) => {
    marker.value = JSON.parse(JSON.stringify(markerTemplate.value));
    topViewStore.onSportChange(template);
    calibrationAssetId.value = null;
  };
  const loadCalibrationAssetsList = async () => {
    try {
      const params = {};
      if (playerStore.videoId) {
        params.video_id = playerStore.videoId;
      }
      const res = await axios.get(`${config.API_LOCATION}/calibration_assets/list`, { params });
      if (res.data.status === "ok") {
        calibrationAssetsList.value = res.data.entries;
        // return res.data.entries;
      }
    } catch (error) {
      console.error("Failed to list calibration assets:", error);
    }
  };
  const loadCalibrationAsset = (id) => {
    const calibrationAsset = calibrationAssetsList.value.find((asset) => asset.id === id);
    if (calibrationAsset) {
      marker.value = calibrationAsset.marker_data;
      videoMarker.value = marker.value.map((m) => m.videoCoordsRel);
      topViewStore.onSportChange(calibrationAsset.template);
      calibrationAssetId.value = id;
      console.log(calibrationAsset);
    }
  };
  const saveCalibrationAsset = async (name, template) => {
    if (isLoading.value || !name || !template) return;
    isLoading.value = true;
    const params = {
      name: name,
      template: template,
      marker_data: [...marker.value],
      video_id: playerStore.videoId,
    };
    try {
      const res = await axios.post(`${config.API_LOCATION}/calibration_assets/create`, params);
      if (res.data.status === "ok") {
        loadCalibrationAssetsList();
      }
    } finally {
      isLoading.value = false;
    }
  };
  const updateCalibrationAsset = async (name, template) => {
    if (isLoading.value || !name || !template) return;
    isLoading.value = true;
    const params = {
      id: calibrationAssetId.value,
      name: name,
      template: template,
      marker_data: [...marker.value],
      video_id: playerStore.videoId,
    };
    try {
      const res = await axios.post(`${config.API_LOCATION}/calibration_assets/update`, params);
      if (res.data.status === "ok") {
        loadCalibrationAssetsList();
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
        loadCalibrationAssetsList();
      }
    } finally {
      isLoading.value = false;
    }
  };

  const hMatrix = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
  ];
  const hMatrixInv = inv(hMatrix);
  function applyHomography(matrix, point) {
    const [x, y, w] = [
      matrix[0][0] * point.x + matrix[0][1] * point.y + matrix[0][2] * 1,
      matrix[1][0] * point.x + matrix[1][1] * point.y + matrix[1][2] * 1,
      matrix[2][0] * point.x + matrix[2][1] * point.y + matrix[2][2] * 1,
    ];
    return { x: x / w, y: y / w };
  }
  const videoMarker = ref([]);
  const fieldPoints = computed(() => {
    return videoMarker.value.map((marker) => applyHomography(hMatrix, marker));
  });

  const reprojectionPoints = computed(() => {
    return fieldPoints.value.map((fieldPoint) => applyHomography(hMatrixInv, fieldPoint));
  });

  return {
    marker,
    markerTemplate,
    allMarkerValid,
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
    calibrationAssetId,
    createCalibrationAsset,
    loadCalibrationAsset,
    loadCalibrationAssetsList,
    saveCalibrationAsset,
    updateCalibrationAsset,
    deleteCalibrationAsset,
    videoMarker,
    fieldPoints,
    reprojectionPoints,
  };
});
