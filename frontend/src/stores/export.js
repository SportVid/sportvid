import { defineStore } from "pinia";
import { ref, computed, toRaw } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { useI18n } from "vue-i18n";
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "./position_data";
import { usePosdataWorkerStore } from "@/stores/posdata_worker";
import { usePlayerStore } from "@/stores/player";
import { useVisualizationStore } from "@/stores/visualization";

export const useExportStore = defineStore("export", () => {
  const topViewStore = useTopViewStore();
  const positionDataStore = usePositionDataStore();

  const { t, te } = useI18n();

  const isLoading = ref(false);

  const exportData = async (format, parameters = [], videoId) => {
    if (isLoading.value) return;
    isLoading.value = true;

    const formData = new FormData();
    if (format !== "positions_csv" && format !== "kpi_csv" && format !== "kpi_aggregated_csv") {
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
      } else if (format === "kpi_csv") {
        exportKpiData(parameters, videoId);
      } else if (format === "kpi_aggregated_csv") {
        exportKpiDataAggregated(parameters, videoId);
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
      id: "timestamp_ms",
      name: t("modal.export.position_data.attributes.timestamp_ms"),
      csv: "timestamp_ms",
      alwaysIncluded: true,
      position: "first",
    },
    {
      id: "player_number",
      name: t("modal.export.position_data.attributes.player_id"),
      csv: "player_id",
      meta: true,
      alwaysIncluded: true,
      position: "first",
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
    {
      id: 3,
      name: t("modal.export.position_data.attributes.x"),
      csv: "x",
      alwaysIncluded: true,
      position: "last",
    },
    {
      id: 4,
      name: t("modal.export.position_data.attributes.y"),
      csv: "y",
      alwaysIncluded: true,
      position: "last",
    },
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
      if (attr.alwaysIncluded) return false;
      if (attr.meta) {
        if (attr.id === "player_name") return hasPlayerMeta;
        if (attr.id === "team_name") return hasTeamMeta;
        return false;
      }
      return presentIndices.has(attr.id);
    });
  });

  const allKpiAttributes = [
    {
      id: "player_name",
      name: t("modal.export.kpi.attributes.player_name"),
      csv: "player_name",
      meta: true,
    },
    { id: "team_id", name: t("modal.export.kpi.attributes.team_id"), csv: "team_id" },
    {
      id: "team_name",
      name: t("modal.export.kpi.attributes.team_name"),
      csv: "team_name",
      meta: true,
    },
  ];

  const selectableKpiAttributes = computed(() => {
    const meta = topViewStore.metaDataTopView;
    const hasPlayerMeta = meta?.player_ids && Object.keys(meta.player_ids).length > 0;
    const hasTeamMeta = meta?.team_ids && Object.keys(meta.team_ids).length > 0;

    return allKpiAttributes.filter((attr) => {
      if (attr.meta) {
        if (attr.id === "player_name") return hasPlayerMeta;
        if (attr.id === "team_name") return hasTeamMeta;
        return false;
      }
      return true;
    });
  });

  const resolveAttrValue = (pos, attr, frameKey) => {
    if (attr.id === "timestamp_ms") return frameKey;
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
    const selectedAttributes =
      parameters.find((p) => p.name === "position_data_attribute")?.value || [];
    const startFrame = parameters.find((p) => p.name === "kpi_start_frame")?.value ?? -Infinity;
    const endFrame = parameters.find((p) => p.name === "kpi_end_frame")?.value ?? Infinity;

    const alwaysFirstAttrs = allPositionDataAttributes.filter(
      (a) => a.alwaysIncluded && a.position === "first"
    );
    const alwaysLastAttrs = allPositionDataAttributes.filter(
      (a) => a.alwaysIncluded && a.position === "last"
    );
    const selectedOptionalAttrs = selectedAttributes
      .map((attrId) => allPositionDataAttributes.find((a) => a.id === attrId))
      .filter(Boolean);

    const attrDefs = [...alwaysFirstAttrs, ...selectedOptionalAttrs, ...alwaysLastAttrs];

    const rawPosData = toRaw(topViewStore.positionDataTopView);
    const filteredPosData = Object.fromEntries(
      Object.entries(rawPosData).filter(([key]) => {
        const t = Number(key);
        return t >= startFrame && t <= endFrame;
      })
    );

    const posdataWorkerStore = usePosdataWorkerStore();
    const csvData = await posdataWorkerStore.exportPositionsCSV(
      filteredPosData,
      toRaw(topViewStore.metaDataTopView),
      attrDefs,
      selectedTeam
    );

    const meta = topViewStore.metaDataTopView;
    const teamNames = Array.isArray(selectedTeam)
      ? selectedTeam.map((id) => meta?.team_ids?.[id]?.name || id).join("-")
      : meta?.team_ids?.[selectedTeam]?.name || selectedTeam;
    const teamSuffix = teamNames.replace(/[\s/\\]+/g, "_");

    const blob = new Blob([csvData], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = `${t("modal.export.position_data.file_name")}_${videoId}_${teamSuffix}.csv`;
    link.click();
  };

  const exportKpiData = async (parameters, videoId) => {
    const visualizationStore = useVisualizationStore();
    const selectedTeam = parameters.find((p) => p.name === "kpi_team")?.value || [];
    const selectedKpiNames = parameters.find((p) => p.name === "kpi_names")?.value || [];
    const selectedAttributes = parameters.find((p) => p.name === "kpi_attribute")?.value || [];
    const startFrame = parameters.find((p) => p.name === "kpi_start_frame")?.value ?? 0;
    const endFrame = parameters.find((p) => p.name === "kpi_end_frame")?.value ?? Infinity;

    const kpiData = toRaw(visualizationStore.kpiData);
    const kpiNames = visualizationStore.kpiNames;
    const meta = topViewStore.metaDataTopView;

    const selectedOptionalAttrs = selectedAttributes
      .map((attrId) => allKpiAttributes.find((a) => a.id === attrId))
      .filter(Boolean);

    // KPI values start at index 2 in each player entry [player_id, team_id, kpi0, kpi1, ...]
    const kpiIndices = selectedKpiNames.map((name) => kpiNames.indexOf(name)).filter((i) => i >= 0);

    const kpiCsvNames = selectedKpiNames.map((name) => {
      const key = `modal.export.kpi.kpi_names.${name}`;
      return te(key) ? t(key) : name;
    });

    const headerRow = [
      "timestamp_ms",
      "player_id",
      ...selectedOptionalAttrs.map((a) => a.csv),
      ...kpiCsvNames,
    ];
    const rows = [headerRow.join(",")];

    const sortedFrames = Object.keys(kpiData)
      .map(Number)
      .sort((a, b) => a - b);
    for (const frameMs of sortedFrames) {
      if (frameMs < startFrame || frameMs > endFrame) continue;
      for (const entry of kpiData[frameMs]) {
        const playerId = entry[0];
        const teamId = entry[1];
        if (selectedTeam.length && !selectedTeam.includes(teamId)) continue;

        const playerNum = meta?.player_ids?.[playerId]?.number;
        const playerIdVal = playerNum != null ? playerNum : playerId;

        const optionalValues = selectedOptionalAttrs.map((attr) => {
          switch (attr.id) {
            case "player_name":
              return meta?.player_ids?.[playerId]?.name || "";
            case "team_id":
              return meta?.team_ids?.[teamId]?.id ?? teamId;
            case "team_name":
              return meta?.team_ids?.[teamId]?.name || "";
            default:
              return "";
          }
        });

        const kpiValues = kpiIndices.map((idx) => entry[2 + idx] ?? "");
        rows.push([frameMs, playerIdVal, ...optionalValues, ...kpiValues].join(","));
      }
    }

    const csvContent = rows.join("\n");
    const teamNames = Array.isArray(selectedTeam)
      ? selectedTeam.map((id) => meta?.team_ids?.[id]?.name || id).join("-")
      : meta?.team_ids?.[selectedTeam]?.name || selectedTeam;
    const teamSuffix = (teamNames || "all").replace(/[\s/\\]+/g, "_");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${t("modal.export.kpi.file_name")}_${videoId}_${teamSuffix}.csv`;
    link.click();
  };

  // Aggregation matching TabWindowKPI:
  // distance_covered: stored as cumulative → compute per-frame delta (dist - prevDist), sum positives
  // velocity:         instantaneous → max
  // metabolic_power:  instantaneous power → sum * dt (converts W to J, i.e. total metabolic work)
  //
  // CSV column names also match TabWindowKPI: distance, velocity_max, metabolic_work.
  const KPI_CSV_NAME = {
    distance_covered: "distance_cumulated",
    velocity: "velocity_max",
    metabolic_power: "metabolic_work_cumulated",
  };

  const exportKpiDataAggregated = async (parameters, videoId) => {
    const visualizationStore = useVisualizationStore();
    const playerStore = usePlayerStore();
    const selectedTeam = parameters.find((p) => p.name === "kpi_team")?.value || [];
    const selectedKpiNames = parameters.find((p) => p.name === "kpi_names")?.value || [];
    const selectedAttributes = parameters.find((p) => p.name === "kpi_attribute")?.value || [];
    const startFrame = parameters.find((p) => p.name === "kpi_start_frame")?.value ?? 0;
    const endFrame = parameters.find((p) => p.name === "kpi_end_frame")?.value ?? Infinity;

    const kpiData = toRaw(visualizationStore.kpiData);
    const kpiNames = visualizationStore.kpiNames;
    const meta = topViewStore.metaDataTopView;
    const dt = 1 / visualizationStore.kpiFramerate;

    const selectedOptionalAttrs = selectedAttributes
      .map((attrId) => allKpiAttributes.find((a) => a.id === attrId))
      .filter(Boolean);

    const kpiCsvNames = selectedKpiNames.map((name) => KPI_CSV_NAME[name] ?? name);

    // playerAgg: { playerId -> { teamId, dist, prevDist, velMax, metpowSum } }
    const playerAgg = {};

    const sortedFrames = Object.keys(kpiData)
      .map(Number)
      .sort((a, b) => a - b);

    for (const frameMs of sortedFrames) {
      if (frameMs < startFrame || frameMs > endFrame) continue;
      for (const entry of kpiData[frameMs]) {
        const playerId = entry[0];
        const teamId = entry[1];
        if (selectedTeam.length && !selectedTeam.includes(teamId)) continue;

        if (!playerAgg[playerId]) {
          playerAgg[playerId] = { teamId, dist: 0, prevDist: null, velMax: null, metpowSum: 0 };
        }
        const agg = playerAgg[playerId];

        for (const kpiName of selectedKpiNames) {
          const kpiIdx = kpiNames.indexOf(kpiName);
          if (kpiIdx < 0) continue;
          const val = entry[2 + kpiIdx];
          if (val == null) continue;

          if (kpiName === "distance_covered") {
            if (agg.prevDist !== null) {
              const inc = val - agg.prevDist;
              if (inc > 0) agg.dist += inc;
            }
            agg.prevDist = val;
          } else if (kpiName === "velocity") {
            agg.velMax = agg.velMax === null ? val : Math.max(agg.velMax, val);
          } else if (kpiName === "metabolic_power") {
            agg.metpowSum += val;
          }
        }
      }
    }

    const headerRow = ["player_id", ...selectedOptionalAttrs.map((a) => a.csv), ...kpiCsvNames];
    const rows = [headerRow.join(",")];

    for (const [playerId, agg] of Object.entries(playerAgg)) {
      const teamId = agg.teamId;
      const playerNum = meta?.player_ids?.[playerId]?.number;
      const playerIdVal = playerNum != null ? playerNum : playerId;

      const optionalValues = selectedOptionalAttrs.map((attr) => {
        switch (attr.id) {
          case "player_name":
            return meta?.player_ids?.[playerId]?.name || "";
          case "team_id":
            return meta?.team_ids?.[teamId]?.id ?? teamId;
          case "team_name":
            return meta?.team_ids?.[teamId]?.name || "";
          default:
            return "";
        }
      });

      const kpiValues = selectedKpiNames.map((name) => {
        if (name === "distance_covered") return agg.dist > 0 ? parseFloat(agg.dist.toFixed(1)) : "";
        if (name === "velocity")
          return agg.velMax !== null ? parseFloat(agg.velMax.toFixed(2)) : "";
        if (name === "metabolic_power")
          return agg.metpowSum > 0 ? parseFloat((agg.metpowSum * dt).toFixed(1)) : "";
        return "";
      });
      rows.push([playerIdVal, ...optionalValues, ...kpiValues].join(","));
    }

    const csvContent = rows.join("\n");
    const teamNames = Array.isArray(selectedTeam)
      ? selectedTeam.map((id) => meta?.team_ids?.[id]?.name || id).join("-")
      : meta?.team_ids?.[selectedTeam]?.name || selectedTeam;
    const teamSuffix = (teamNames || "all").replace(/[\s/\\]+/g, "_");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${t("modal.export.kpi_aggregated.file_name")}_${videoId}_${teamSuffix}.csv`;
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
    selectableKpiAttributes,
  };
});
