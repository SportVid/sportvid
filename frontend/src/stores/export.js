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
    {
      id: "player_number",
      name: t("modal.export.position_data.attributes.player_id"),
      csv: "player_id",
      meta: true,
    },
    {
      id: "player_name",
      name: t("modal.export.position_data.attributes.player_name"),
      csv: "player_name",
      meta: true,
    },
    { id: 1, name: t("modal.export.position_data.attributes.team_id"), csv: "team_id" },
    {
      id: "team_name",
      name: t("modal.export.position_data.attributes.team_name"),
      csv: "team_name",
      meta: true,
    },
    { id: 2, name: t("modal.export.position_data.attributes.game_section"), csv: "game_section" },
    { id: 3, name: t("modal.export.position_data.attributes.x"), csv: "x", locked: true },
    { id: 4, name: t("modal.export.position_data.attributes.y"), csv: "y", locked: true },
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

    const meta = topViewStore.metaDataTopView;
    const hasPlayerMeta = meta?.player_ids && Object.keys(meta.player_ids).length > 0;
    const hasTeamMeta = meta?.team_ids && Object.keys(meta.team_ids).length > 0;

    return allPositionDataAttributes.filter((attr) => {
      if (attr.meta) {
        if (attr.id === "player_number" || attr.id === "player_name") return hasPlayerMeta;
        if (attr.id === "team_name") return hasTeamMeta;
        return false;
      }
      return presentIndices.has(attr.id);
    });
  });

  const allRunningDistanceAttributes = [
    {
      id: "player_id",
      name: t("modal.export.running_distance.attributes.player_id"),
      csv: "player_id",
    },
    {
      id: "player_name",
      name: t("modal.export.running_distance.attributes.player_name"),
      csv: "player_name",
      meta: true,
    },
    { id: "team_id", name: t("modal.export.running_distance.attributes.team_id"), csv: "team_id" },
    {
      id: "team_name",
      name: t("modal.export.running_distance.attributes.team_name"),
      csv: "team_name",
      meta: true,
    },
    {
      id: "distance",
      name: t("modal.export.running_distance.attributes.distance"),
      csv: "distance",
      locked: true,
    },
  ];

  const selectableRunningDistanceAttributes = computed(() => {
    const meta = topViewStore.metaDataTopView;
    const hasPlayerMeta = meta?.player_ids && Object.keys(meta.player_ids).length > 0;
    const hasTeamMeta = meta?.team_ids && Object.keys(meta.team_ids).length > 0;

    return allRunningDistanceAttributes.filter((attr) => {
      if (attr.meta) {
        if (attr.id === "player_name") return hasPlayerMeta;
        if (attr.id === "team_name") return hasTeamMeta;
        return false;
      }
      return true;
    });
  });

  const resolveAttrValue = (pos, attr) => {
    const meta = topViewStore.metaDataTopView;
    if (attr.meta) {
      const playerId = pos[0];
      const teamId = pos[1];
      switch (attr.id) {
        case "player_number": {
          const num = meta?.player_ids?.[playerId]?.number;
          return num != null ? num : playerId;
        }
        case "player_name": {
          return meta?.player_ids?.[playerId]?.name || "";
        }
        case "team_name": {
          return meta?.team_ids?.[teamId]?.name || "";
        }
        default:
          return "";
      }
    }
    if (attr.csv === "team_id") {
      const teamId = pos[1];
      return meta?.team_ids?.[teamId]?.id || teamId;
    }
    return pos[attr.id];
  };

  const exportPositionData = async (parameters = [], videoId) => {
    const selectedTeam = parameters.find((p) => p.name === "position_data_team")?.value;
    const selectedAttributes = parameters.find((p) => p.name === "position_data_attribute")?.value;

    const attrDefs = selectedAttributes.map((attrId) =>
      allPositionDataAttributes.find((a) => a.id === attrId)
    );

    const csvHeader = attrDefs.map((a) => a.csv).join(",");
    const csvRows = Object.entries(topViewStore.positionDataTopView)
      .map(([_, positions]) =>
        positions
          .filter((pos) => selectedTeam.includes(pos[1]) || pos[1] === selectedTeam)
          .map((pos) => {
            return attrDefs
              .map((attr) => {
                const val = resolveAttrValue(pos, attr);
                if (typeof val === "string" && (val.includes(",") || val.includes('"'))) {
                  return `"${val.replace(/"/g, '""')}"`;
                }
                return val;
              })
              .join(",");
          })
          .join("\n")
      )
      .join("\n");

    const meta = topViewStore.metaDataTopView;
    const teamNames = Array.isArray(selectedTeam)
      ? selectedTeam.map((id) => meta?.team_ids?.[id]?.name || id).join("-")
      : meta?.team_ids?.[selectedTeam]?.name || selectedTeam;
    const teamSuffix = teamNames.replace(/[\s/\\]+/g, "_");

    const blob = new Blob([csvHeader + "\n" + csvRows], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = `${t("modal.export.position_data.file_name")}_${videoId}_${teamSuffix}.csv`;
    link.click();
  };

  const exportRunningDistanceData = (parameters, videoId) => {
    const selectedTeam = parameters.find((p) => p.name === "running_distance_team")?.value || [];
    const selectedAttributes =
      parameters.find((p) => p.name === "running_distance_attribute")?.value || [];
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

    const meta = topViewStore.metaDataTopView;
    const attrDefs = selectedAttributes
      .map((attrId) => allRunningDistanceAttributes.find((a) => a.id === attrId))
      .filter(Boolean);

    const csvHeader = attrDefs.map((a) => a.csv).join(",");
    const csvRows = distances
      .map((p) => {
        return attrDefs
          .map((attr) => {
            let val;
            switch (attr.id) {
              case "player_id":
                val = meta?.player_ids?.[p.player_id]?.number ?? p.player_id;
                break;
              case "player_name":
                val = meta?.player_ids?.[p.player_id]?.name || "";
                break;
              case "team_id":
                val = meta?.team_ids?.[p.team_id]?.id || p.team_id;
                break;
              case "team_name":
                val = meta?.team_ids?.[p.team_id]?.name || p.team_id;
                break;
              case "distance":
                val = p.distance.toFixed(2);
                break;
              default:
                val = "";
            }
            if (typeof val === "string" && (val.includes(",") || val.includes('"'))) {
              return `"${val.replace(/"/g, '""')}"`;
            }
            return val;
          })
          .join(",");
      })
      .join("\n");

    const meta2 = topViewStore.metaDataTopView;
    const teamNames = Array.isArray(selectedTeam)
      ? selectedTeam.map((id) => meta2?.team_ids?.[id]?.name || id).join("-")
      : meta2?.team_ids?.[selectedTeam]?.name || selectedTeam;
    const teamSuffix = teamNames.replace(/[\s/\\]+/g, "_");

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
    selectableRunningDistanceAttributes,
  };
});
