/**
 * CompactPositionData - Column-oriented TypedArray storage for position data.
 *
 * Reduces memory from ~300-500MB (nested JS objects for 135k frames) to ~45MB
 * by storing player data in contiguous typed arrays instead of per-frame arrays
 * of boxed JS numbers.
 *
 * Data layout:
 *   timestamps[i]  = millisecond timestamp of frame i
 *   frameOffsets[i] = start index in player arrays for frame i
 *   frameOffsets[i+1] - frameOffsets[i] = number of players in frame i
 *
 *   playerIds[offset], teamIds[offset], gameSections[offset],
 *   xCoords[offset], yCoords[offset] = data for one player entry
 */

export class CompactPositionData {
  /**
   * @param {Float64Array} timestamps - sorted frame timestamps in ms
   * @param {Uint32Array} frameOffsets - start offset per frame (length = timestamps.length + 1)
   * @param {Int32Array} playerIds
   * @param {Uint8Array} teamIds
   * @param {Uint8Array} gameSections
   * @param {Float32Array} xCoords
   * @param {Float32Array} yCoords
   */
  constructor(timestamps, frameOffsets, playerIds, teamIds, gameSections, xCoords, yCoords) {
    this.timestamps = timestamps;
    this.frameOffsets = frameOffsets;
    this.playerIds = playerIds;
    this.teamIds = teamIds;
    this.gameSections = gameSections;
    this.xCoords = xCoords;
    this.yCoords = yCoords;
    this.frameCount = timestamps.length;
    this.totalPlayers = playerIds.length;
  }

  /**
   * Binary search: find index of largest timestamp <= target.
   * Returns -1 if target < timestamps[0].
   */
  getFrameIndex(targetMs) {
    const ts = this.timestamps;
    if (!ts.length) return -1;
    if (targetMs < ts[0]) return -1;
    if (targetMs >= ts[ts.length - 1]) return ts.length - 1;

    let lo = 0;
    let hi = ts.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >>> 1;
      if (ts[mid] <= targetMs) {
        lo = mid;
      } else {
        hi = mid - 1;
      }
    }
    return lo;
  }

  /**
   * Get players for frame at index i as [[pid, tid, gs, x, y], ...].
   * Materializes only one frame (~23 entries) - negligible overhead.
   */
  getFrameByIndex(i) {
    if (i < 0 || i >= this.frameCount) return [];
    const start = this.frameOffsets[i];
    const end = this.frameOffsets[i + 1];
    const result = new Array(end - start);
    for (let j = start; j < end; j++) {
      result[j - start] = [
        this.playerIds[j],
        this.teamIds[j],
        this.gameSections[j],
        this.xCoords[j],
        this.yCoords[j],
      ];
    }
    return result;
  }

  /**
   * Get players for a given timestamp (finds closest frame <= timestampMs).
   */
  getFrame(timestampMs) {
    const idx = this.getFrameIndex(timestampMs);
    return this.getFrameByIndex(idx);
  }

  /**
   * Get the timestamp at frame index i.
   */
  getTimestamp(i) {
    return i >= 0 && i < this.frameCount ? this.timestamps[i] : undefined;
  }

  /**
   * Get frame index range [startIdx, endIdx] for timestamps in [startMs, endMs].
   * Returns null if no frames in range.
   */
  getFrameRange(startMs, endMs) {
    if (!this.frameCount) return null;
    const ts = this.timestamps;

    // Find first frame >= startMs
    let lo = 0;
    let hi = ts.length - 1;
    if (startMs > ts[hi]) return null;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (ts[mid] < startMs) lo = mid + 1;
      else hi = mid;
    }
    const startIdx = lo;

    // Find last frame <= endMs
    lo = startIdx;
    hi = ts.length - 1;
    if (endMs < ts[startIdx]) return null;
    while (lo < hi) {
      const mid = (lo + hi + 1) >>> 1;
      if (ts[mid] <= endMs) lo = mid;
      else hi = mid - 1;
    }
    const endIdx = lo;

    return { startIdx, endIdx };
  }

  /**
   * Materialize a plain-object subset {timestamp: [[pid,tid,gs,x,y],...]} for
   * the given time range. Used to send data to web workers via postMessage.
   */
  toSubsetObject(startMs, endMs) {
    const range = this.getFrameRange(startMs, endMs);
    if (!range) return {};

    const result = {};
    for (let i = range.startIdx; i <= range.endIdx; i++) {
      result[this.timestamps[i]] = this.getFrameByIndex(i);
    }
    return result;
  }

  /**
   * Get all timestamps as a plain number array (for sortedFrameKeys compatibility).
   * Caches result since timestamps don't change.
   */
  getTimestampArray() {
    if (!this._timestampArray) {
      this._timestampArray = Array.from(this.timestamps);
    }
    return this._timestampArray;
  }
}

/**
 * Convert a plain pos_data object {timestamp_ms: [[pid,tid,gs,x,y],...]}
 * into a CompactPositionData instance.
 *
 * Also precomputes metadata (player list, game sections, halftime boundaries)
 * in the same pass to avoid a second scan.
 *
 * @param {Object} posDataObj - raw position data object from backend
 * @returns {{ compact: CompactPositionData, playerList: Array, playerIdSet: Set, gameSections: Set, halftimeBoundaries: Object }}
 */
export function fromPosDataObject(posDataObj) {
  const rawKeys = Object.keys(posDataObj);
  const keys = new Array(rawKeys.length);
  for (let i = 0; i < rawKeys.length; i++) keys[i] = Number(rawKeys[i]);
  keys.sort((a, b) => a - b);

  // First pass: count total player entries
  let totalPlayers = 0;
  for (let i = 0; i < keys.length; i++) {
    totalPlayers += posDataObj[keys[i]].length;
  }

  // Allocate typed arrays
  const timestamps = new Float64Array(keys.length);
  const frameOffsets = new Uint32Array(keys.length + 1);
  const playerIds = new Int32Array(totalPlayers);
  const teamIds = new Uint8Array(totalPlayers);
  const gameSections = new Uint8Array(totalPlayers);
  const xCoords = new Float32Array(totalPlayers);
  const yCoords = new Float32Array(totalPlayers);

  // Metadata extraction split by entity kind. team_id semantics:
  //   0 = ball, 1 = inactive, 2 = ref, ≥3 = active player team
  // playerMap holds active players only (used by KPI/heatmap selection);
  // separate maps for ball/ref/inactive feed the top-view toggle UI.
  const playerMap = new Map(); // active players (team_id ≥ 3)
  const refMap = new Map();
  const ballMap = new Map();
  const inactiveMap = new Map();
  const sectionsSet = new Set();
  const boundaries = {};

  let offset = 0;
  for (let i = 0; i < keys.length; i++) {
    const t = keys[i];
    timestamps[i] = t;
    frameOffsets[i] = offset;

    const players = posDataObj[t];
    for (let j = 0; j < players.length; j++) {
      const p = players[j];
      playerIds[offset] = p[0];
      teamIds[offset] = p[1];
      gameSections[offset] = p[2];
      xCoords[offset] = p[3];
      yCoords[offset] = p[4];
      offset++;

      const tid = p[1];
      if (tid === 0) ballMap.set(p[0], tid);
      else if (tid === 2) refMap.set(p[0], tid);
      else if (tid === 1) inactiveMap.set(p[0], tid);
      else playerMap.set(p[0], tid);

      const gs = p[2];
      sectionsSet.add(gs);
      if (!boundaries[gs]) {
        boundaries[gs] = { first: t, last: t };
      } else {
        if (t > boundaries[gs].last) boundaries[gs].last = t;
        // keys are sorted, so first is always correct from initial set
      }
    }
  }
  frameOffsets[keys.length] = offset;

  const compact = new CompactPositionData(
    timestamps,
    frameOffsets,
    playerIds,
    teamIds,
    gameSections,
    xCoords,
    yCoords
  );

  const _toList = (map) =>
    Array.from(map, ([pid, tid]) => ({ playerId: pid, teamId: tid })).sort(
      (a, b) => a.playerId - b.playerId
    );

  return {
    compact,
    playerList: _toList(playerMap),
    refList: _toList(refMap),
    ballList: _toList(ballMap),
    inactiveList: _toList(inactiveMap),
    playerIdSet: new Set(playerMap.keys()),
    gameSections: sectionsSet,
    halftimeBoundaries: boundaries,
  };
}
