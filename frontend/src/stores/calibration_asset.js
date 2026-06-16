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
    const calibrationMode = ref(false);

    const calibrationAssetType = ref("marker");
    const setCalibrationAssetType = (type) => {
      calibrationAssetType.value = type;
    };

    const calibrationSport = ref("soccer");

    const calibrationAssetObjects = ref([]);
    const sportTemplates = {
      soccer: {
        marker: [
          {
            name: "Corner-top-left",
            id: "1",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-top-right",
            id: "2",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-bottom-left",
            id: "3",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-bottom-right",
            id: "4",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Midline-top",
            id: "5",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Midline-bottom",
            id: "6",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Kick-off",
            id: "7",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0.5, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Kick-off-circle-top",
            id: "8",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0.6325, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Kick-off-circle-bottom",
            id: "9",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0.3675, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-left",
            id: "10",
            active: false,
            compAreaCoordsRel: [{ x: 0.105, y: 0.5, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-area-left-corner-top",
            id: "11",
            active: false,
            compAreaCoordsRel: [{ x: 0.1575, y: 0.7975, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-area-left-corner-bottom",
            id: "12",
            active: false,
            compAreaCoordsRel: [{ x: 0.1575, y: 0.2025, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-line-left-penalty-area-top",
            id: "13",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.7975, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-line-left-penalty-area-bottom",
            id: "14",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.2025, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-arc-left-top",
            id: "15",
            active: false,
            compAreaCoordsRel: [{ x: 0.1575, y: 0.605, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-arc-left-bottom",
            id: "16",
            active: false,
            compAreaCoordsRel: [{ x: 0.1575, y: 0.395, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-right",
            id: "17",
            active: false,
            compAreaCoordsRel: [{ x: 0.895, y: 0.5, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-area-right-corner-top",
            id: "18",
            active: false,
            compAreaCoordsRel: [{ x: 0.8425, y: 0.7975, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-area-right-corner-bottom",
            id: "19",
            active: false,
            compAreaCoordsRel: [{ x: 0.8425, y: 0.2025, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-line-right-penalty-area-top",
            id: "20",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.7975, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-line-right-penalty-area-bottom",
            id: "21",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.2025, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-arc-right-top",
            id: "22",
            active: false,
            compAreaCoordsRel: [{ x: 0.8425, y: 0.605, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Penalty-arc-right-bottom",
            id: "23",
            active: false,
            compAreaCoordsRel: [{ x: 0.8425, y: 0.395, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-area-left-corner-top",
            id: "24",
            active: false,
            compAreaCoordsRel: [{ x: 0.05, y: 0.635, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-area-left-corner-bottom",
            id: "25",
            active: false,
            compAreaCoordsRel: [{ x: 0.05, y: 0.365, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-line-left-goal-area-top",
            id: "26",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.635, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-line-left-goal-area-bottom",
            id: "27",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.365, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-area-right-corner-top",
            id: "28",
            active: false,
            compAreaCoordsRel: [{ x: 0.95, y: 0.635, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-area-right-corner-bottom",
            id: "29",
            active: false,
            compAreaCoordsRel: [{ x: 0.95, y: 0.365, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-line-right-goal-area-top",
            id: "30",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.635, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-line-right-goal-area-bottom",
            id: "31",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.365, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
        ],
        segment: [
          {
            name: "Sideline-top-left",
            id: "1",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 1, z: 0 },
              { x: 0.5, y: 1, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-top-right",
            id: "2",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 1, z: 0 },
              { x: 1, y: 1, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-bottom-left",
            id: "3",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0, z: 0 },
              { x: 0.5, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-bottom-right",
            id: "4",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0, z: 0 },
              { x: 1, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-left",
            id: "5",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 1, z: 0 },
              { x: 0, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-right",
            id: "6",
            active: false,
            compAreaCoordsRel: [
              { x: 1, y: 1, z: 0 },
              { x: 1, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Midline",
            id: "7",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 1, z: 0 },
              { x: 0.5, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Kick-off-circle-left",
            id: "8",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0.64, z: 0 },
              { x: 0.436, y: 0.598, z: 0 },
              { x: 0.41, y: 0.5, z: 0 },
              { x: 0.436, y: 0.402, z: 0 },
              { x: 0.5, y: 0.36, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Kick-off-circle-right",
            id: "9",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0.64, z: 0 },
              { x: 0.564, y: 0.598, z: 0 },
              { x: 0.59, y: 0.5, z: 0 },
              { x: 0.564, y: 0.402, z: 0 },
              { x: 0.5, y: 0.36, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Penalty-area-left-top",
            id: "10",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.7975, z: 0 },
              { x: 0.1575, y: 0.7975, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Penalty-area-left-bottom",
            id: "11",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.2025, z: 0 },
              { x: 0.1575, y: 0.2025, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Penalty-area-left-main",
            id: "12",
            active: false,
            compAreaCoordsRel: [
              { x: 0.1575, y: 0.7975, z: 0 },
              { x: 0.1575, y: 0.2025, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Penalty-area-left-circle",
            active: false,
            compAreaCoordsRel: [
              { x: 0.1575, y: 0.61, z: 0 },
              { x: 0.1825, y: 0.565, z: 0 },
              { x: 0.1925, y: 0.5, z: 0 },
              { x: 0.1825, y: 0.435, z: 0 },
              { x: 0.1575, y: 0.39, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Penalty-area-right-top",
            id: "14",
            active: false,
            compAreaCoordsRel: [
              { x: 0.8425, y: 0.7975, z: 0 },
              { x: 1, y: 0.7975, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Penalty-area-right-bottom",
            id: "15",
            active: false,
            compAreaCoordsRel: [
              { x: 0.8425, y: 0.2025, z: 0 },
              { x: 1, y: 0.2025, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Penalty-area-right-main",
            id: "16",
            active: false,
            compAreaCoordsRel: [
              { x: 0.8425, y: 0.7975, z: 0 },
              { x: 0.8425, y: 0.2025, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Penalty-area-right-circle",
            id: "17",
            active: false,
            compAreaCoordsRel: [
              { x: 0.8425, y: 0.61, z: 0 },
              { x: 0.8175, y: 0.565, z: 0 },
              { x: 0.8075, y: 0.5, z: 0 },
              { x: 0.8175, y: 0.435, z: 0 },
              { x: 0.8425, y: 0.39, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Goal-area-left-top",
            id: "18",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.635, z: 0 },
              { x: 0.05, y: 0.635, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Goal-area-left-bottom",
            id: "19",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.365, z: 0 },
              { x: 0.05, y: 0.365, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Goal-area-left-main",
            id: "20",
            active: false,
            compAreaCoordsRel: [
              { x: 0.05, y: 0.635, z: 0 },
              { x: 0.05, y: 0.365, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Goal-area-right-top",
            id: "21",
            active: false,
            compAreaCoordsRel: [
              { x: 0.95, y: 0.635, z: 0 },
              { x: 1, y: 0.635, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Goal-area-right-bottom",
            id: "22",
            active: false,
            compAreaCoordsRel: [
              { x: 0.95, y: 0.365, z: 0 },
              { x: 1, y: 0.365, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Goal-area-right-main",
            id: "23",
            active: false,
            compAreaCoordsRel: [
              { x: 0.95, y: 0.635, z: 0 },
              { x: 0.95, y: 0.365, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
        ],
      },
      handball: {
        marker: [
          {
            name: "Corner-top-left",
            id: "1",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-top-right",
            id: "2",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-bottom-left",
            id: "3",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-bottom-right",
            id: "4",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Midline-top",
            id: "5",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Midline-bottom",
            id: "6",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Centre-circle-top",
            id: "8",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0.65, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Centre-circle-bottom",
            id: "9",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0.35, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "7-m-line-left",
            id: "10",
            active: false,
            compAreaCoordsRel: [{ x: 0.175, y: 0.5, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "7-m-line-right",
            id: "11",
            active: false,
            compAreaCoordsRel: [{ x: 0.825, y: 0.5, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "4-m-line-right",
            id: "12",
            active: false,
            compAreaCoordsRel: [{ x: 0.1, y: 0.5, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "4-m-line-right",
            id: "13",
            active: false,
            compAreaCoordsRel: [{ x: 0.9, y: 0.5, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-area-line-left-top",
            id: "14",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.875, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-area-line-left-bottom",
            id: "15",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.125, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-area-line-right-top",
            id: "16",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.875, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Goal-area-line-right-bottom",
            id: "17",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.125, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Free-throw-line-left-top",
            id: "18",
            active: false,
            compAreaCoordsRel: [{ x: 0.0775, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Free-throw-line-left-bottom",
            id: "19",
            active: false,
            compAreaCoordsRel: [{ x: 0.0775, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Free-throw-line-right-top",
            id: "20",
            active: false,
            compAreaCoordsRel: [{ x: 0.9225, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Free-throw-line-right-bottom",
            id: "21",
            active: false,
            compAreaCoordsRel: [{ x: 0.9225, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
        ],
        segment: [
          {
            name: "Sideline-top-left",
            id: "1",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 1, z: 0 },
              { x: 0.5, y: 1, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-top-right",
            id: "2",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 1, z: 0 },
              { x: 1, y: 1, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-bottom-left",
            id: "3",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0, z: 0 },
              { x: 0.5, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-bottom-right",
            id: "4",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0, z: 0 },
              { x: 1, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-left",
            id: "5",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 1, z: 0 },
              { x: 0, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-right",
            id: "6",
            active: false,
            compAreaCoordsRel: [
              { x: 1, y: 1, z: 0 },
              { x: 1, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Midline-top",
            id: "7",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 1, z: 0 },
              { x: 0.5, y: 0.65, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Midline-bottom",
            id: "8",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0.35, z: 0 },
              { x: 0.5, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Centre-circle-left",
            id: "9",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0.65, z: 0 },
              { x: 0.447, y: 0.6061, z: 0 },
              { x: 0.425, y: 0.5, z: 0 },
              { x: 0.447, y: 0.3939, z: 0 },
              { x: 0.5, y: 0.35, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Centre-circle-right",
            id: "10",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0.65, z: 0 },
              { x: 0.553, y: 0.6061, z: 0 },
              { x: 0.575, y: 0.5, z: 0 },
              { x: 0.553, y: 0.3939, z: 0 },
              { x: 0.5, y: 0.35, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Goal-area-left-circle",
            id: "11",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.875, z: 0 },
              { x: 0.106, y: 0.787, z: 0 },
              { x: 0.15, y: 0.575, z: 0 },
              { x: 0.15, y: 0.425, z: 0 },
              { x: 0.106, y: 0.213, z: 0 },
              { x: 0, y: 0.125, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Goal-area-right-circle",
            id: "12",
            active: false,
            compAreaCoordsRel: [
              { x: 1, y: 0.875, z: 0 },
              { x: 0.894, y: 0.787, z: 0 },
              { x: 0.85, y: 0.575, z: 0 },
              { x: 0.85, y: 0.425, z: 0 },
              { x: 0.894, y: 0.213, z: 0 },
              { x: 1, y: 0.125, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Free-throw-area-left-circle",
            id: "13",
            active: false,
            compAreaCoordsRel: [
              { x: 0.0775, y: 1, z: 0 },
              { x: 0.195, y: 0.8, z: 0 },
              { x: 0.225, y: 0.575, z: 0 },
              { x: 0.225, y: 0.425, z: 0 },
              { x: 0.195, y: 0.2, z: 0 },
              { x: 0.0775, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Free-throw-area-right-circle",
            id: "14",
            active: false,
            compAreaCoordsRel: [
              { x: 0.9225, y: 1, z: 0 },
              { x: 0.805, y: 0.8, z: 0 },
              { x: 0.775, y: 0.575, z: 0 },
              { x: 0.775, y: 0.425, z: 0 },
              { x: 0.805, y: 0.2, z: 0 },
              { x: 0.9225, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
        ],
      },
      basketball: {
        marker: [
          {
            name: "Corner-top-left",
            id: "1",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-top-right",
            id: "2",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-bottom-left",
            id: "3",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-bottom-right",
            id: "4",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Midline-top",
            id: "5",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Midline-bottom",
            id: "6",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Centre-circle-top",
            id: "7",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0.62, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Centre-circle-bottom",
            id: "8",
            active: false,
            compAreaCoordsRel: [{ x: 0.5, y: 0.38, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-break-mark-top-left",
            id: "9",
            active: false,
            compAreaCoordsRel: [{ x: 0.29, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-break-mark-top-right",
            id: "10",
            active: false,
            compAreaCoordsRel: [{ x: 0.71, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-break-mark-bottom-left",
            id: "11",
            active: false,
            compAreaCoordsRel: [{ x: 0.29, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-break-mark-bottom-right",
            id: "12",
            active: false,
            compAreaCoordsRel: [{ x: 0.71, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-line-left-top-left",
            id: "13",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.94, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-line-left-top-right",
            id: "14",
            active: false,
            compAreaCoordsRel: [{ x: 0.15, y: 0.94, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-line-left-bottom-left",
            id: "15",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.06, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-line-left-bottom-right",
            id: "16",
            active: false,
            compAreaCoordsRel: [{ x: 0.15, y: 0.06, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-line-right-top-left",
            id: "17",
            active: false,
            compAreaCoordsRel: [{ x: 0.85, y: 0.94, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-line-right-top-right",
            id: "18",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.94, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-line-right-bottom-left",
            id: "19",
            active: false,
            compAreaCoordsRel: [{ x: 0.85, y: 0.06, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "3-point-line-right-bottom-right",
            id: "20",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.06, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "key-left-top-left",
            id: "21",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.66, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "key-left-top-right",
            id: "22",
            active: false,
            compAreaCoordsRel: [{ x: 0.2025, y: 0.66, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "key-left-bottom-left",
            id: "23",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0.34, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "key-left-bottom-right",
            id: "24",
            active: false,
            compAreaCoordsRel: [{ x: 0.2025, y: 0.34, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "key-right-top-left",
            id: "25",
            active: false,
            compAreaCoordsRel: [{ x: 0.7975, y: 0.66, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "key-right-top-right",
            id: "26",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.66, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "key-right-bottom-left",
            id: "27",
            active: false,
            compAreaCoordsRel: [{ x: 0.7975, y: 0.34, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "key-right-bottom-right",
            id: "28",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0.34, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
        ],
        segment: [
          {
            name: "Sideline-top-left",
            id: "1",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 1, z: 0 },
              { x: 0.5, y: 1, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-top-right",
            id: "2",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 1, z: 0 },
              { x: 1, y: 1, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-bottom-left",
            id: "3",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0, z: 0 },
              { x: 0.5, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-bottom-right",
            id: "4",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0, z: 0 },
              { x: 1, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-left",
            id: "5",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 1, z: 0 },
              { x: 0, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Sideline-right",
            id: "6",
            active: false,
            compAreaCoordsRel: [
              { x: 1, y: 1, z: 0 },
              { x: 1, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Midline-top",
            id: "7",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 1, z: 0 },
              { x: 0.5, y: 0.62, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Midline-bottom",
            id: "8",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0.38, z: 0 },
              { x: 0.5, y: 0, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Centre-circle-left",
            id: "9",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0.62, z: 0 },
              { x: 0.455, y: 0.5761, z: 0 },
              { x: 0.4375, y: 0.5, z: 0 },
              { x: 0.455, y: 0.4239, z: 0 },
              { x: 0.5, y: 0.38, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Centre-circle-right",
            id: "10",
            active: false,
            compAreaCoordsRel: [
              { x: 0.5, y: 0.62, z: 0 },
              { x: 0.545, y: 0.5761, z: 0 },
              { x: 0.5625, y: 0.5, z: 0 },
              { x: 0.545, y: 0.4239, z: 0 },
              { x: 0.5, y: 0.38, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "3-point-line-left-top",
            id: "11",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.94, z: 0 },
              { x: 0.15, y: 0.94, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "3-point-line-left-bottom",
            id: "12",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.06, z: 0 },
              { x: 0.15, y: 0.06, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "3-point-line-left-circle",
            id: "13",
            active: false,
            compAreaCoordsRel: [
              { x: 0.15, y: 0.94, z: 0 },
              { x: 0.2775, y: 0.72, z: 0 },
              { x: 0.3075, y: 0.5, z: 0 },
              { x: 0.2775, y: 0.28, z: 0 },
              { x: 0.15, y: 0.06, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "3-point-line-right-top",
            id: "14",
            active: false,
            compAreaCoordsRel: [
              { x: 0.85, y: 0.94, z: 0 },
              { x: 1, y: 0.94, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "3-point-line-right-bottom",
            id: "15",
            active: false,
            compAreaCoordsRel: [
              { x: 0.85, y: 0.06, z: 0 },
              { x: 1, y: 0.06, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "3-point-line-right-circle",
            id: "16",
            active: false,
            compAreaCoordsRel: [
              { x: 0.85, y: 0.94, z: 0 },
              { x: 0.7225, y: 0.72, z: 0 },
              { x: 0.6925, y: 0.5, z: 0 },
              { x: 0.7225, y: 0.28, z: 0 },
              { x: 0.85, y: 0.06, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Key-left-top",
            id: "17",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.66, z: 0 },
              { x: 0.2025, y: 0.66, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Key-left-bottom",
            id: "18",
            active: false,
            compAreaCoordsRel: [
              { x: 0, y: 0.34, z: 0 },
              { x: 0.2025, y: 0.34, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Key-left-right",
            id: "19",
            active: false,
            compAreaCoordsRel: [
              { x: 0.2025, y: 0.66, z: 0 },
              { x: 0.2025, y: 0.34, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Key-left-circle",
            id: "20",
            active: false,
            compAreaCoordsRel: [
              { x: 0.2025, y: 0.615, z: 0 },
              { x: 0.2525, y: 0.5575, z: 0 },
              { x: 0.2625, y: 0.5, z: 0 },
              { x: 0.2525, y: 0.4425, z: 0 },
              { x: 0.2025, y: 0.385, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Key-right-top",
            id: "21",
            active: false,
            compAreaCoordsRel: [
              { x: 0.7975, y: 0.66, z: 0 },
              { x: 1, y: 0.66, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Key-right-bottom",
            id: "22",
            active: false,
            compAreaCoordsRel: [
              { x: 0.7975, y: 0.34, z: 0 },
              { x: 1, y: 0.34, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Key-right-left",
            id: "23",
            active: false,
            compAreaCoordsRel: [
              { x: 0.7975, y: 0.66, z: 0 },
              { x: 0.7975, y: 0.34, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
          {
            name: "Key-right-circle",
            id: "24",
            active: false,
            compAreaCoordsRel: [
              { x: 0.7975, y: 0.615, z: 0 },
              { x: 0.7475, y: 0.5575, z: 0 },
              { x: 0.7375, y: 0.5, z: 0 },
              { x: 0.7475, y: 0.4425, z: 0 },
              { x: 0.7975, y: 0.385, z: 0 },
            ],
            videoCoordsRel: [
              { x: null, y: null, z: null },
              { x: null, y: null, z: null },
            ],
          },
        ],
      },
      climbing: {
        marker: [
          {
            name: "Corner-top-left",
            id: "1",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-top-right",
            id: "2",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 1, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-bottom-left",
            id: "3",
            active: false,
            compAreaCoordsRel: [{ x: 0, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
          {
            name: "Corner-bottom-right",
            id: "4",
            active: false,
            compAreaCoordsRel: [{ x: 1, y: 0, z: 0 }],
            videoCoordsRel: [{ x: null, y: null, z: null }],
          },
        ],
        segment: [
          {
            name: "Border-top",
            id: "1",
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
            name: "Border-bottom",
            id: "2",
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
            name: "Border-left",
            id: "3",
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
            name: "Border-right",
            id: "4",
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
        ],
      },
    };
    const currentTemplate = computed(() => {
      const templates = sportTemplates[calibrationSport.value] ?? sportTemplates.soccer;
      return calibrationAssetType.value === "marker" ? templates.marker : templates.segment;
    });

    const PALETTE = [
      // Tableau 20 (industry standard for categorical data viz)
      "#4E79A7",
      "#F28E2B",
      "#E15759",
      "#76B7B2",
      "#59A14F",
      "#EDC948",
      "#B07AA1",
      "#FF9DA7",
      "#9C755F",
      "#BAB0AC",
      "#A0CBE8",
      "#FFBE7D",
      "#FF9D9A",
      "#86BCB6",
      "#8CD17D",
      "#F1CE63",
      "#D4A6C8",
      "#FABFD2",
      "#D7B5A6",
      "#79706E",
      // ColorBrewer Set1 + Set2
      "#e41a1c",
      "#377eb8",
      "#4daf4a",
      "#984ea3",
      "#ff7f00",
      "#a65628",
      "#f781bf",
      "#66c2a5",
      "#fc8d62",
      "#8da0cb",
      "#e78ac3",
      "#a6d854",
      "#ffd92f",
      "#e5c494",
      // D3 category10 extras + ColorBrewer Dark2
      "#1b9e77",
      "#d95f02",
      "#7570b3",
      "#e7298a",
      "#66a61e",
      "#e6ab02",
      "#a6761d",
      "#393b79",
      "#637939",
      "#8c6d31",
      "#843c39",
      "#7b4173",
      "#5254a3",
      "#636363",
      "#f0027f",
      "#bf5b17",
      "#386cb0",
      "#beaed4",
      "#7fc97f",
      "#fdc086",
    ];
    const objectColorMap = computed(() => {
      const map = {};
      calibrationAssetObjects.value.forEach((obj, i) => {
        map[obj.id] = PALETTE[i % PALETTE.length];
      });
      return map;
    });

    const allAssetObjectsValid = computed(
      () =>
        calibrationAssetObjects.value.filter((object) =>
          object.videoCoordsRel.some((p) => p.x !== null && p.y !== null)
        ).length >= 4
    );

    const isAddingCustomMarker = ref(false);

    const filteredReferenceObjects = computed(() => {
      return calibrationAssetObjects.value.filter((object) =>
        object.videoCoordsRel.some((p) => p.x !== null && p.y !== null)
      );
    });

    const isAnyReferenceObjectActive = computed(() =>
      calibrationAssetObjects.value.some((object) => object.active)
    );

    const toggleObject = (event, id) => {
      event.stopPropagation();

      calibrationAssetObjects.value = calibrationAssetObjects.value.map((object) => ({
        ...object,
        active: object.id === id ? !object.active : false,
      }));
    };
    const addCustomMarker = () => {
      if (!isAddingCustomMarker.value) {
        isAddingCustomMarker.value = true;

        const customObjectCount = calibrationAssetObjects.value.filter((m) =>
          m.name.startsWith("Custom-object")
        ).length;
        const newObject = {
          name: `Custom-object-${customObjectCount + 1}`,
          id: calibrationAssetObjects.value.length + 1,
          active: false,
          compAreaCoordsRel: [{ x: null, y: null, z: null }],
          videoCoordsRel: [{ x: null, y: null, z: null }],
        };

        calibrationAssetObjects.value.push(newObject);
      }
    };
    const placeCustomMarker = (event) => {
      if (isAddingCustomMarker.value) {
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
                1 -
                (event.clientY -
                  (topViewStore.topViewSize.top +
                    ((1 - topViewStore.currentSport.heightRel) / 2) *
                      topViewStore.topViewSize.height)) /
                  (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel),
            },
          ];
        }

        isAddingCustomMarker.value = false;
      }
    };
    const deleteCustomMarker = (id) => {
      calibrationAssetObjects.value = calibrationAssetObjects.value.filter((m) => m.id !== id);
    };
    const placeCustomMarkerByCoords = (relX, relY) => {
      const lastObject = calibrationAssetObjects.value[calibrationAssetObjects.value.length - 1];
      if (lastObject) {
        lastObject.compAreaCoordsRel = [{ x: relX, y: relY, z: 0 }];
      }
      isAddingCustomMarker.value = false;
    };
    const unmapObject = (id) => {
      const obj = calibrationAssetObjects.value.find((o) => o.id === id);
      if (!obj) return;
      obj.videoCoordsRel = obj.videoCoordsRel.map(() => ({ x: null, y: null, z: null }));
      isAssetEdited.value = true;
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
    const createCalibrationAsset = ({ sport, objectType }) => {
      calibrationAssetType.value = objectType;
      topViewStore.onSportChange(sport);
      calibrationSport.value = topViewStore.currentSport.key;
      calibrationAssetObjects.value = JSON.parse(JSON.stringify(currentTemplate.value));

      calibrationAssetId.value = null;
      calibrationMatrixPersisted.value = [];
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
        }
      } catch (error) {
        console.error("Failed to list calibration assets:", error);
      }
    };
    const loadCalibrationAsset = (id) => {
      const calibrationAsset = calibrationAssetsList.value.find((asset) => asset.id === id);
      if (calibrationAsset) {
        calibrationAssetType.value = calibrationAsset.object_type;
        topViewStore.onSportChange(calibrationAsset.sport);
        calibrationSport.value = topViewStore.currentSport.key;
        calibrationAssetObjects.value = calibrationAsset.object_data;

        calibrationAssetId.value = id;
        calibrationMatrixPersisted.value = [];
      }
    };
    const saveCalibrationAsset = async (name, sport, objectType) => {
      if (isLoading.value || !name || !sport) return;
      isLoading.value = true;
      const params = {
        name: name,
        sport: sport,
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
    const updateCalibrationAsset = async (name, sport, objectType) => {
      if (isLoading.value || !name || !sport) return;
      isLoading.value = true;
      const params = {
        id: calibrationAssetId.value,
        name: name,
        sport: sport,
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

    const resetCalibrationAsset = () => {
      calibrationMode.value = false;
      calibrationAssetObjects.value = [];
      calibrationAssetId.value = null;
      calibrationMatrixPersisted.value = [];
      isAssetEdited.value = false;
      timeChangeConflict.value = false;
      videoObjectTime.value = null;
      showVideoAsset.value = false;
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
    const videoObject = computed(() => calibrationAssetObjects.value.map((m) => m.videoCoordsRel));
    const topViewObjectProjection = computed(() => {
      if (!calibrationMatrix.value) return [];
      return videoObject.value
        .filter((pointList) => pointList.some((p) => p.x !== null && p.y !== null))
        .map((pointList) => pointList.map((p) => applyHomography(calibrationMatrix.value, p)));
    });
    const videoObjectReprojection = computed(() => {
      if (!calibrationMatrixInv.value) return [];
      return topViewObjectProjection.value.map((pointList) =>
        pointList.map((p) => applyHomography(calibrationMatrixInv.value, p))
      );
    });

    return {
      calibrationAssetObjects,
      currentTemplate,
      allAssetObjectsValid,
      filteredReferenceObjects,
      filteredVideoObject,
      toggleObject,
      isAnyReferenceObjectActive,
      isAddingCustomMarker,
      addCustomMarker,
      placeCustomMarker,
      deleteCustomMarker,
      unmapObject,
      placeCustomMarkerByCoords,
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
      objectColorMap,
      calibrationMode,
      calibrationSport,
      resetCalibrationAsset,
      calibrationAssetSaveSuccess,
      calibrationAssetUpdateSuccess,
      calibrationAssetDeleteSuccess,
      timeChangeConflict,
      videoObjectTime,
      isAssetEdited,
      calibrationAssetType,
      setCalibrationAssetType,
    };
  },
  {
    persist: {
      pick: [
        "calibrationMode",
        "calibrationSport",
        "calibrationAssetType",
        "calibrationAssetObjects",
        "calibrationMatrixPersisted",
      ],
      storage: sessionStorage,
    },
  }
);
