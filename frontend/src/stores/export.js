import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { useI18n } from "vue-i18n";
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "./position_data";

export const useExportStore = defineStore("export", () => {
  const topViewStore = useTopViewStore();
  const positionDataStore = usePositionDataStore();

  const { t } = useI18n();

  const isLoading = ref(false);

  const exportData = async (format, parameters = [], videoId) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const formData = new FormData();
    if (format !== "positions_csv") {
      formData.append("format", format);
      let jsonParameters = [];
      parameters.forEach((p) => {
        if ("file" in p) {
          formData.append(`file_${p.name}`, p.file);
        } else {
          jsonParameters.push(p);
        }
      });
      formData.append("parameters", JSON.stringify(jsonParameters));
      formData.append("video_id", videoId);
    }

    try {
      if (format === "positions_csv") {
        exportPositionData(parameters, videoId);
      } else if (format === "running_distance_csv") {
        exportRunningDistanceData(parameters, videoId);
      } else {
        const res = await axios.post(`${config.API_LOCATION}/video/export`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        if (res.data.status === "ok") {
          exportTimelineData(res.data, videoId);
        }
      }
    } finally {
      isLoading.value = false;
    }
  };

  const allPositionDataAttributes = [
    { id: 0, name: t("modal.export.position_data.attributes.player_id"), csv: "player_id" },
    { id: 1, name: t("modal.export.position_data.attributes.team_id"), csv: "team_id" },
    { id: 2, name: t("modal.export.position_data.attributes.game_section"), csv: "game_section" },
    { id: 3, name: t("modal.export.position_data.attributes.x"), csv: "x" },
    { id: 4, name: t("modal.export.position_data.attributes.y"), csv: "y" },
    { id: 5, name: t("modal.export.position_data.attributes.bbox_id"), csv: "bbox_id" },
    { id: 6, name: t("modal.export.position_data.attributes.bbox_left"), csv: "bbox_left" },
    { id: 7, name: t("modal.export.position_data.attributes.bbox_top"), csv: "bbox_top" },
    { id: 8, name: t("modal.export.position_data.attributes.bbox_width"), csv: "bbox_width" },
    { id: 9, name: t("modal.export.position_data.attributes.bbox_height"), csv: "bbox_height" },
    { id: 10, name: t("modal.export.position_data.attributes.det_score"), csv: "det_score" },
  ];
  const selectablePositionDataAttributes = computed(() => {
    const presentIndices = new Set(
      Object.values(topViewStore.positionDataTopView)
        .flat()
        .flatMap((pos) => pos.map((_, idx) => idx))
    );

    return allPositionDataAttributes.filter((attr) => presentIndices.has(attr.id));
  });

  const exportPositionData = async (parameters = [], videoId) => {
    const selectedTeam = parameters.find((p) => p.name === "position_data_team")?.value;
    const selectedAttributes = parameters.find((p) => p.name === "position_data_attribute")?.value;

    const csvHeader = selectedAttributes.map((i) => allPositionDataAttributes[i].csv).join(",");
    const csvRows = Object.entries(topViewStore.positionDataTopView)
      .map(([_, positions]) =>
        positions
          .filter((pos) => selectedTeam.includes(pos[1]) || pos[1] === selectedTeam)
          .map((pos) => selectedAttributes.map((i) => pos[i]).join(","))
          .join("\n")
      )
      .join("\n");

    const teamSuffix = Array.isArray(selectedTeam) ? selectedTeam.join("-") : selectedTeam;

    const blob = new Blob([csvHeader + "\n" + csvRows], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = `${t("modal.export.position_data.file_name")}_${videoId}_${teamSuffix}.csv`;
    link.click();
  };

  const exportRunningDistanceData = (parameters, videoId) => {
    const selectedTeam = parameters.find((p) => p.name === "running_distance_team")?.value || [];
    const startFrame =
      parameters.find((p) => p.name === "running_distance_start_frame")?.value ?? 0;
    const endFrame = parameters.find((p) => p.name === "running_distance_end_frame")?.value ?? 0;

    const allPlayers = new Set();
    Object.values(topViewStore.positionDataTopView).forEach((frame) => {
      frame.forEach((p) => {
        if (!selectedTeam.length || selectedTeam.includes(p[1])) allPlayers.add(p[0]);
      });
    });

    const distances = positionDataStore.calculateRunningDistances(allPlayers, startFrame, endFrame);

    const csvHeader = "player_id,team_id,distance";
    const csvRows = distances
      .map((p) => `${p.player_id},${p.team_id},${p.distance.toFixed(2)}`)
      .join("\n");

    const teamSuffix = Array.isArray(selectedTeam) ? selectedTeam.join("-") : selectedTeam;

    const blob = new Blob([csvHeader + "\n" + csvRows], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${t("modal.export.running_distance.file_name")}_${videoId}_${teamSuffix}.csv`;
    link.click();
  };

  const exportTimelineData = (data, videoId) => {
    if (data.extension === "zip") {
      const filecontent = Buffer.from(data.file, "base64");
      let blob = new Blob([filecontent], { type: "application/zip" });
      let link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = `timelines.${data.extension}`;
      link.click();
    } else if (data.extension === "csv" || data.extension === "eaf") {
      let blob = new Blob([data.file], { type: `text/${data.extension}` });
      let link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = `${videoId}.${data.extension}`;
      link.click();
    }
  };

  return {
    exportData,
    selectablePositionDataAttributes,
  };
});
