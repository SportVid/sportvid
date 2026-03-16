import { defineStore } from "pinia";
import { ref } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";

/**
 * Module-level in-memory cache: trackingDataId -> { posData, metaData }
 * Lives for the browser session (cleared on page reload).
 * Replaces IndexedDB to avoid the structuredClone overhead on write/read.
 */
const _posDataCache = new Map();

export const usePosdataWorkerStore = defineStore("posdataWorker", () => {
  let worker = null;
  let requestCounter = 0;
  const pendingRequests = new Map();

  const isLoading = ref(false);
  const loadProgress = ref(0);
  const isCalculating = ref(false);

  function getWorker() {
    if (!worker) {
      worker = new Worker("/workers/posdata.worker.js");
      worker.onmessage = handleWorkerMessage;
      worker.onerror = (err) => console.error("PosData Worker error:", err);
    }
    return worker;
  }

  function handleWorkerMessage(e) {
    const { id, data, error, type } = e.data;
    const pending = pendingRequests.get(id);
    if (!pending) return;

    if (type === "ERROR") {
      pending.reject(new Error(error));
    } else {
      pending.resolve(data);
    }
    pendingRequests.delete(id);
  }

  function sendToWorker(msg) {
    return new Promise((resolve, reject) => {
      const id = ++requestCounter;
      pendingRequests.set(id, { resolve, reject });
      getWorker().postMessage({ ...msg, id });
    });
  }

  /**
   * Return cached { posData, metaData } for a trackingDataId, or null.
   */
  function getCached(trackingDataId) {
    return _posDataCache.get(trackingDataId) || null;
  }

  /**
   * Store posData + metaData in the in-memory cache.
   */
  function cacheData(trackingDataId, posData, metaData) {
    _posDataCache.set(trackingDataId, { posData, metaData });
  }

  /**
   * Load position data in chunks from backend API.
   * Returns { posData, metaData } or null on failure.
   */
  async function loadChunked(trackingDataId, videoId) {
    isLoading.value = true;
    loadProgress.value = 0;

    try {
      // Check in-memory cache first
      const cached = _posDataCache.get(trackingDataId);
      if (cached) {
        loadProgress.value = 100;
        return { posData: cached.posData, metaData: cached.metaData };
      }

      // Load from backend in chunks
      let offset = 0;
      const limit = 10000;
      let total = null;
      let metaData = null;
      const allFrames = {};

      while (total === null || offset < total) {
        const res = await axios.get(`${config.API_LOCATION}/tracking_data/pos_data/chunk`, {
          params: { tracking_data_id: trackingDataId, video_id: videoId, offset, limit },
        });

        if (res.data.status !== "ok") throw new Error("Chunk load failed");

        Object.assign(allFrames, res.data.frames);
        total = res.data.total;
        if (res.data.meta_data) metaData = res.data.meta_data;

        offset += limit;
        loadProgress.value = Math.min(
          99,
          Math.round((Object.keys(allFrames).length / total) * 100)
        );
      }

      // Store in in-memory cache
      const result = { posData: allFrames, metaData: metaData || {} };
      _posDataCache.set(trackingDataId, result);

      loadProgress.value = 100;
      return result;
    } catch (err) {
      console.error("Chunk loading failed:", err);
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Calculate running distances in the Web Worker.
   * @param {Object} posData - raw (non-proxy) pos_data object
   */
  async function calcRunningDistances(
    posData,
    playerIds,
    startFrame,
    endFrame,
    fieldLength,
    fieldWidth,
    zones = []
  ) {
    isCalculating.value = true;
    try {
      // Extract only needed frame range to reduce structured-clone overhead
      const subset = extractRange(posData, startFrame, endFrame);

      return await sendToWorker({
        type: "CALC_RUNNING_DISTANCE",
        posData: subset,
        playerIds: Array.from(playerIds),
        startFrame,
        endFrame,
        fieldLength,
        fieldWidth,
        zones,
      });
    } finally {
      isCalculating.value = false;
    }
  }

  /**
   * Calculate heatmap/movement points in the Web Worker.
   */
  async function calcHeatmapPoints(posData, playerIds, startFrame, endFrame, cropPct) {
    isCalculating.value = true;
    try {
      const subset = extractRange(posData, startFrame, endFrame);

      return await sendToWorker({
        type: "CALC_HEATMAP_POINTS",
        posData: subset,
        playerIds: Array.from(playerIds),
        startFrame,
        endFrame,
        cropPct,
      });
    } finally {
      isCalculating.value = false;
    }
  }

  /**
   * Export positions CSV in the Web Worker. Returns CSV string.
   */
  async function exportPositionsCSV(posData, metaData, attrDefs, selectedTeam) {
    return await sendToWorker({
      type: "EXPORT_POSITIONS_CSV",
      posData,
      metaData,
      attrDefs,
      selectedTeam,
    });
  }

  /**
   * Export running distance CSV in the Web Worker. Returns CSV string.
   */
  async function exportRunningDistanceCSV(
    posData,
    metaData,
    attrDefs,
    playerIds,
    startFrame,
    endFrame,
    fieldLength,
    fieldWidth,
    selectedTeam
  ) {
    return await sendToWorker({
      type: "EXPORT_RUNNING_DISTANCE_CSV",
      posData,
      metaData,
      attrDefs,
      playerIds: Array.from(playerIds),
      startFrame,
      endFrame,
      fieldLength,
      fieldWidth,
      selectedTeam: Array.isArray(selectedTeam) ? selectedTeam : [selectedTeam],
    });
  }

  /**
   * Extract frames in [start, end] from posData to reduce clone size.
   */
  function extractRange(posData, start, end) {
    const subset = {};
    for (const key of Object.keys(posData)) {
      const t = Number(key);
      if (t >= start && t <= end) subset[key] = posData[key];
    }
    return subset;
  }

  return {
    isLoading,
    loadProgress,
    isCalculating,
    loadChunked,
    getCached,
    cacheData,
    calcRunningDistances,
    calcHeatmapPoints,
    exportPositionsCSV,
    exportRunningDistanceCSV,
  };
});
