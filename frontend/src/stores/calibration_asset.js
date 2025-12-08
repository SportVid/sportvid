import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { inv } from "mathjs";
import { useTopViewStore } from "./top_view";
import { usePlayerStore } from "@/stores/player";

export const useCalibrationAssetStore = defineStore(
  "calibration_asset",
  () => {
    const topViewStore = useTopViewStore();
    const playerStore = usePlayerStore();

    const isLoading = ref(false);

    const calibrationAssetType = ref("segment");
    const setCalibrationAssetType = (type) => {
      calibrationAssetType.value = type;
    };
    const toggleCalibrationAssetType = () => {
      calibrationAssetType.value = calibrationAssetType.value === "marker" ? "segment" : "marker";
    };

    const calibrationAssetObjects = ref([]);
    const markerTemplate = ref([
      {
        name: "Corner-top-left",
        id: "1",
        set: true,
        active: false,
        compAreaCoordsRel: [{ x: 0, y: 0, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Corner-top-right",
        id: "2",
        set: true,
        active: false,
        compAreaCoordsRel: [{ x: 1, y: 0, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Corner-bottom-left",
        id: "3",
        set: true,
        active: false,
        compAreaCoordsRel: [{ x: 0, y: 1, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Corner-bottom-right",
        id: "4",
        set: true,
        active: false,
        compAreaCoordsRel: [{ x: 1, y: 1, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Midline-top",
        id: "5",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.5, y: 0, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Midline-bottom",
        id: "6",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.5, y: 1, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Kick-off",
        id: "7",
        set: true,
        active: false,
        compAreaCoordsRel: [{ x: 0.5, y: 0.5, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Kick-off-circle-top",
        id: "8",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.5, y: 0.36, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Kick-off-circle-bottom",
        id: "9",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.5, y: 0.64, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Penalty-left",
        id: "10",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.11, y: 0.5, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Penalty-area-left-corner-top",
        id: "11",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.165, y: 0.19, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Penalty-area-left-corner-bottom",
        id: "12",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.165, y: 0.81, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Penalty-right",
        id: "13",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.89, y: 0.5, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Penalty-area-right-corner-top",
        id: "14",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.835, y: 0.19, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Penalty-area-right-corner-bottom",
        id: "15",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.835, y: 0.81, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Goal-area-left-corner-top",
        id: "16",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.055, y: 0.36, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Goal-area-left-corner-bottom",
        id: "17",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.055, y: 0.64, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Goal-area-right-corner-top",
        id: "18",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.945, y: 0.36, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
      {
        name: "Goal-area-right-corner-bottom",
        id: "19",
        set: false,
        active: false,
        compAreaCoordsRel: [{ x: 0.945, y: 0.64, z: 0 }],
        videoCoordsRel: [{ x: null, y: null, z: null }],
      },
    ]);
    const segmentTemplate = ref([
      {
        name: "Sideline-top",
        id: "1",
        set: true,
        active: false,
        compAreaCoordsRel: [
          { x: 0, y: 0, z: 0 },
          { x: 1, y: 0, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Sideline-bottom",
        id: "2",
        set: true,
        active: false,
        compAreaCoordsRel: [
          { x: 0, y: 1, z: 0 },
          { x: 1, y: 1, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Sideline-left",
        id: "3",
        set: true,
        active: false,
        compAreaCoordsRel: [
          { x: 0, y: 0, z: 0 },
          { x: 0, y: 1, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Sideline-right",
        id: "4",
        set: true,
        active: false,
        compAreaCoordsRel: [
          { x: 1, y: 0, z: 0 },
          { x: 1, y: 1, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Midline",
        id: "5",
        set: true,
        active: false,
        compAreaCoordsRel: [
          { x: 0.5, y: 0, z: 0 },
          { x: 0.5, y: 1, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Kick-off-circle-left",
        id: "6",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.5, y: 0.36, z: 0 },
          { x: 0.436, y: 0.402, z: 0 },
          { x: 0.41, y: 0.5, z: 0 },
          { x: 0.436, y: 0.598, z: 0 },
          { x: 0.5, y: 0.64, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Kick-off-circle-right",
        id: "7",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.5, y: 0.36, z: 0 },
          { x: 0.564, y: 0.402, z: 0 },
          { x: 0.59, y: 0.5, z: 0 },
          { x: 0.564, y: 0.598, z: 0 },
          { x: 0.5, y: 0.64, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Penalty-area-left-top",
        id: "7",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0, y: 0.19, z: 0 },
          { x: 0.165, y: 0.19, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Penalty-area-left-bottom",
        id: "8",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0, y: 0.81, z: 0 },
          { x: 0.165, y: 0.81, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Penalty-area-left-main",
        id: "9",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.165, y: 0.19, z: 0 },
          { x: 0.165, y: 0.81, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Penalty-area-left-circle",
        id: "10",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.165, y: 0.39, z: 0 },
          { x: 0.19, y: 0.435, z: 0 },
          { x: 0.2, y: 0.5, z: 0 },
          { x: 0.19, y: 0.565, z: 0 },
          { x: 0.165, y: 0.61, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Penalty-area-right-top",
        id: "11",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.835, y: 0.19, z: 0 },
          { x: 1, y: 0.19, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Penalty-area-right-bottom",
        id: "12",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.835, y: 0.81, z: 0 },
          { x: 1, y: 0.81, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Penalty-area-right-main",
        id: "13",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.835, y: 0.19, z: 0 },
          { x: 0.835, y: 0.81, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Penalty-area-right-circle",
        id: "14",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.835, y: 0.39, z: 0 },
          { x: 0.81, y: 0.435, z: 0 },
          { x: 0.8, y: 0.5, z: 0 },
          { x: 0.81, y: 0.565, z: 0 },
          { x: 0.835, y: 0.61, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Goal-area-left-top",
        id: "15",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0, y: 0.36, z: 0 },
          { x: 0.055, y: 0.36, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Goal-area-left-bottom",
        id: "16",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0, y: 0.64, z: 0 },
          { x: 0.055, y: 0.64, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Goal-area-left-main",
        id: "17",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.055, y: 0.36, z: 0 },
          { x: 0.055, y: 0.64, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Goal-area-right-top",
        id: "18",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.945, y: 0.36, z: 0 },
          { x: 1, y: 0.36, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Goal-area-right-bottom",
        id: "19",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.945, y: 0.64, z: 0 },
          { x: 1, y: 0.64, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
      {
        name: "Goal-area-right-main",
        id: "20",
        set: false,
        active: false,
        compAreaCoordsRel: [
          { x: 0.945, y: 0.36, z: 0 },
          { x: 0.945, y: 0.64, z: 0 },
        ],
        videoCoordsRel: [
          { x: null, y: null, z: null },
          { x: null, y: null, z: null },
        ],
      },
    ]);
    const currentTemplate = computed(() => {
      return calibrationAssetType.value === "marker" ? markerTemplate.value : segmentTemplate.value;
    });

    const allAssetObjectsValid = computed(() =>
      calibrationAssetObjects.value.every(
        (m) => m.videoCoordsRel.x !== null && m.videoCoordsRel.y !== null
      )
    );

    const isAddingReferenceObject = ref(false);

    const filteredReferenceObjects = computed(() => {
      return calibrationAssetObjects.value.filter(
        (object) =>
          object.compAreaCoordsRel.every((p) => p.x !== null && p.y !== null) && object.set
      );
    });

    const isAnyReferenceObjectActive = computed(() =>
      calibrationAssetObjects.value.some((object) => object.active)
    );

    const toggleReferenceObject = (event, id) => {
      event.stopPropagation();

      calibrationAssetObjects.value = calibrationAssetObjects.value.map((object) => ({
        ...object,
        active: object.id === id ? !object.active : false,
      }));
    };
    const addReferenceObject = () => {
      if (!isAddingReferenceObject.value) {
        isAddingReferenceObject.value = true;

        const customObjectCount = calibrationAssetObjects.value.filter((m) =>
          m.name.startsWith("Custom-object")
        ).length;
        const newObject = {
          name: `Custom-object-${customObjectCount + 1}`,
          id: calibrationAssetObjects.value.length + 1,
          set: true,
          active: false,
          compAreaCoordsRel: [{ x: null, y: null, z: null }],
          videoCoordsRel: [{ x: null, y: null, z: null }],
        };

        calibrationAssetObjects.value.push(newObject);
      }
    };
    const addTemplateReferenceObject = (m) => {
      m.set = true;
      calibrationAssetObjects.value.push(m);
    };
    const setReferenceObject = (event) => {
      if (isAddingReferenceObject.value) {
        const lastObject = calibrationAssetObjects.value[calibrationAssetObjects.value.length - 1];
        if (lastObject) {
          lastObject.compAreaCoordsRel = [
            {
              x:
                (event.clientX -
                  (topViewStore.topViewSize.left +
                    ((1 - topViewStore.currentSport.widthRel) / 2) *
                      topViewStore.topViewSize.width)) /
                (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel),
              y:
                (event.clientY -
                  (topViewStore.topViewSize.top +
                    ((1 - topViewStore.currentSport.heightRel) / 2) *
                      topViewStore.topViewSize.height)) /
                (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel),
            },
          ];
        }

        isAddingReferenceObject.value = false;
      }
    };
    const deleteReferenceObject = (id) => {
      calibrationAssetObjects.value = calibrationAssetObjects.value.filter((m) => m.id !== id);
    };

    const timeChangeConflict = ref(false);
    const videoObjectTime = ref(null);
    const isAssetEdited = ref(false);

    const showVideoAsset = ref(false);
    const previousShowVideoAsset = ref(false);
    const hoveredVideoObject = ref(null);
    const filteredVideoObject = computed(() => {
      return calibrationAssetObjects.value.filter((object) =>
        object.videoCoordsRel.some((p) => p.x !== null && p.y !== null)
      );
    });

    const setVideoObject = (coords) => {
      const activeObject = calibrationAssetObjects.value.find((m) => m.active);
      if (!activeObject) return;

      activeObject.videoCoordsRel = coords.map((p) => ({
        x: p.x ?? null,
        y: p.y ?? null,
        z: p.z ?? null,
      }));
      isAssetEdited.value = true;
      activeObject.active = false;
    };

    const toggleVideoAsset = () => {
      showVideoAsset.value = !showVideoAsset.value;
    };

    const calibrationAssetsList = ref({});
    const calibrationAssetId = ref(null);
    const calibrationAssetSaveSuccess = ref(false);
    const calibrationAssetUpdateSuccess = ref(false);
    const calibrationAssetDeleteSuccess = ref(false);
    const createCalibrationAsset = ({ template, objectType }) => {
      calibrationAssetType.value = objectType;
      calibrationAssetObjects.value = JSON.parse(
        JSON.stringify(currentTemplate.value.filter((m) => m.set))
      );
      topViewStore.onSportChange(template);

      calibrationAssetId.value = null;
      videoObject.value = [];
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
        calibrationAssetType.value = calibrationAsset.object_type;
        calibrationAssetObjects.value = calibrationAsset.object_data;
        videoObject.value = calibrationAssetObjects.value.map((m) => m.videoCoordsRel);
        topViewStore.onSportChange(calibrationAsset.template);

        calibrationAssetId.value = id;
      }
    };
    const saveCalibrationAsset = async (name, template, objectType) => {
      if (isLoading.value || !name || !template) return;
      isLoading.value = true;
      const params = {
        name: name,
        template: template,
        object_type: objectType,
        object_data: [...calibrationAssetObjects.value],
        video_id: playerStore.videoId,
      };
      try {
        const res = await axios.post(`${config.API_LOCATION}/calibration_assets/create`, params);
        if (res.data.status === "ok") {
          calibrationAssetSaveSuccess.value = true;
          isAssetEdited.value = false;
          timeChangeConflict.value = false;
          loadCalibrationAssetsList();
        }
      } finally {
        isLoading.value = false;
      }
    };
    const updateCalibrationAsset = async (name, template, objectType) => {
      if (isLoading.value || !name || !template) return;
      isLoading.value = true;
      const params = {
        id: calibrationAssetId.value,
        name: name,
        template: template,
        object_type: objectType,
        object_data: [...calibrationAssetObjects.value],
        video_id: playerStore.videoId,
      };
      try {
        const res = await axios.post(`${config.API_LOCATION}/calibration_assets/update`, params);
        if (res.data.status === "ok") {
          calibrationAssetUpdateSuccess.value = true;
          isAssetEdited.value = false;
          timeChangeConflict.value = false;
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
          calibrationAssetDeleteSuccess.value = true;
          loadCalibrationAssetsList();
        }
      } finally {
        isLoading.value = false;
      }
    };

    const identityMatrix = [
      [1, 0, 0],
      [0, 1, 0],
      [0, 0, 1],
    ];
    const calibrationMatrixPersisted = ref([]);
    const calibrationMatrix = computed(() => {
      if (
        Array.isArray(calibrationMatrixPersisted.value) &&
        calibrationMatrixPersisted.value.length > 0
      ) {
        return calibrationMatrixPersisted.value;
      }
      const asset = Object.values(calibrationAssetsList.value).find(
        (item) => item.id === calibrationAssetId.value
      );
      const m = asset?.homography_matrix;
      calibrationMatrixPersisted.value =
        JSON.stringify(m) === JSON.stringify(identityMatrix) ? null : m;
      if (!m) return null;
      return JSON.stringify(m) === JSON.stringify(identityMatrix) ? null : m;
    });
    const calibrationMatrixInv = computed(() => {
      if (!calibrationMatrix.value) return null;
      return inv(calibrationMatrix.value);
    });

    function applyHomography(matrix, point) {
      const X = matrix[0][0] * point.x + matrix[0][1] * point.y + matrix[0][2] * 1;
      const Y = matrix[1][0] * point.x + matrix[1][1] * point.y + matrix[1][2] * 1;
      const W = matrix[2][0] * point.x + matrix[2][1] * point.y + matrix[2][2] * 1;

      return { x: X / W, y: Y / W };
    }
    const videoObject = ref([]);
    const topViewObjectProjection = computed(() => {
      if (!calibrationMatrix.value) return [];
      return videoObject.value.map((object) => applyHomography(calibrationMatrix.value, object));
    });

    const videoObjectReprojection = computed(() => {
      if (!calibrationMatrixInv.value) return [];
      return topViewObjectProjection.value.map((point) =>
        applyHomography(calibrationMatrixInv.value, point)
      );
    });

    return {
      calibrationAssetObjects,
      currentTemplate,
      markerTemplate,
      segmentTemplate,
      allAssetObjectsValid,
      filteredReferenceObjects,
      filteredVideoObject,
      toggleReferenceObject,
      isAnyReferenceObjectActive,
      isAddingReferenceObject,
      addReferenceObject,
      addTemplateReferenceObject,
      setReferenceObject,
      deleteReferenceObject,
      setVideoObject,
      showVideoAsset,
      previousShowVideoAsset,
      toggleVideoAsset,
      hoveredVideoObject,
      calibrationAssetsList,
      calibrationAssetId,
      createCalibrationAsset,
      loadCalibrationAsset,
      loadCalibrationAssetsList,
      saveCalibrationAsset,
      updateCalibrationAsset,
      deleteCalibrationAsset,
      calibrationMatrix,
      calibrationMatrixPersisted,
      calibrationMatrixInv,
      videoObject,
      topViewObjectProjection,
      videoObjectReprojection,
      applyHomography,
      calibrationAssetSaveSuccess,
      calibrationAssetUpdateSuccess,
      calibrationAssetDeleteSuccess,
      timeChangeConflict,
      videoObjectTime,
      isAssetEdited,
      calibrationAssetType,
      setCalibrationAssetType,
      toggleCalibrationAssetType,
    };
  },
  {
    persist: {
      pick: [
        "calibrationAssetType",
        "calibrationAssetObjects",
        "videoObject",
        "calibrationMatrixPersisted",
      ],
      storage: sessionStorage,
    },
  }
);
