/**
 * Position Data Web Worker
 *
 * Handles heavy computation off the main thread:
 * - Running distance calculation
 * - Heatmap / movement point generation
 * - CSV export generation
 *
 * Communication via postMessage. Each request carries a unique `id`
 * so the main thread can match responses to promises.
 */

/* eslint-disable no-restricted-globals */
self.onmessage = function (e) {
  var msg = e.data;
  var type = msg.type;
  var id = msg.id;

  try {
    switch (type) {
      case "CALC_RUNNING_DISTANCE":
        handleRunningDistance(id, msg);
        break;
      case "CALC_HEATMAP_POINTS":
        handleHeatmapPoints(id, msg);
        break;
      case "EXPORT_POSITIONS_CSV":
        handleExportPositionsCSV(id, msg);
        break;
      case "EXPORT_RUNNING_DISTANCE_CSV":
        handleExportRunningDistanceCSV(id, msg);
        break;
      default:
        self.postMessage({ type: "ERROR", id: id, error: "Unknown command: " + type });
    }
  } catch (err) {
    self.postMessage({ type: "ERROR", id: id, error: err.message || String(err) });
  }
};

// ---------------------------------------------------------------------------
// Running Distance
// ---------------------------------------------------------------------------

function handleRunningDistance(id, msg) {
  var posData = msg.posData;
  var playerIds = msg.playerIds;
  var startFrame = msg.startFrame;
  var endFrame = msg.endFrame;
  var fieldLength = msg.fieldLength;
  var fieldWidth = msg.fieldWidth;

  var playerIdsSet = {};
  for (var pi = 0; pi < playerIds.length; pi++) {
    playerIdsSet[playerIds[pi]] = true;
  }

  var allTimes = Object.keys(posData).map(Number);
  var timeRange = [];
  for (var ti = 0; ti < allTimes.length; ti++) {
    if (allTimes[ti] >= startFrame && allTimes[ti] <= endFrame) {
      timeRange.push(allTimes[ti]);
    }
  }
  timeRange.sort(function (a, b) {
    return a - b;
  });

  // Collect all players (excluding ball = teamId 1)
  var allPlayers = {};
  for (var fi = 0; fi < allTimes.length; fi++) {
    var players = posData[allTimes[fi]];
    if (!players) continue;
    for (var j = 0; j < players.length; j++) {
      var p = players[j];
      if (p[1] === 1) continue;
      if (!(p[0] in allPlayers)) {
        allPlayers[p[0]] = { player_id: p[0], team_id: p[1], distance: 0 };
      }
    }
  }

  // Accumulate distances
  if (timeRange.length > 1) {
    for (var i = 1; i < timeRange.length; i++) {
      var tPrev = timeRange[i - 1];
      var tCurr = timeRange[i];
      var prev = posData[tPrev];
      var curr = posData[tCurr];
      if (!prev || !curr) continue;

      // Build lookup for prev frame
      var prevMap = {};
      for (var k = 0; k < prev.length; k++) {
        prevMap[prev[k][0]] = prev[k];
      }

      for (var c = 0; c < curr.length; c++) {
        var cp = curr[c];
        if (cp[1] === 1) continue;
        var pp = prevMap[cp[0]];
        if (!pp) continue;

        var dx = (cp[3] - pp[3]) * fieldLength;
        var dy = (cp[4] - pp[4]) * fieldWidth;
        var dist = Math.sqrt(dx * dx + dy * dy);

        if (!(cp[0] in allPlayers)) {
          allPlayers[cp[0]] = { player_id: cp[0], team_id: cp[1], distance: 0 };
        }
        allPlayers[cp[0]].distance += dist;
      }
    }
  }

  var result = [];
  var keys = Object.keys(allPlayers);
  for (var ri = 0; ri < keys.length; ri++) {
    var item = allPlayers[keys[ri]];
    if (playerIdsSet[item.player_id]) {
      result.push({
        player_id: item.player_id,
        team_id: item.team_id,
        distance: parseFloat(item.distance.toFixed(1)),
      });
    }
  }
  result.sort(function (a, b) {
    return a.player_id - b.player_id;
  });

  self.postMessage({ type: "RUNNING_DISTANCE_RESULT", id: id, data: result });
}

// ---------------------------------------------------------------------------
// Heatmap / Movement Points
// ---------------------------------------------------------------------------

function handleHeatmapPoints(id, msg) {
  var posData = msg.posData;
  var playerIds = msg.playerIds;
  var startFrame = msg.startFrame;
  var endFrame = msg.endFrame;
  var cropPct = msg.cropPct || { x: [0, 1], y: [0, 1] };

  var pidSet = {};
  for (var i = 0; i < playerIds.length; i++) {
    pidSet[playerIds[i]] = true;
  }

  var allPositions = [];
  var frameKeys = Object.keys(posData);
  for (var fi = 0; fi < frameKeys.length; fi++) {
    var t = Number(frameKeys[fi]);
    if (t < startFrame || t > endFrame) continue;
    var arr = posData[frameKeys[fi]];
    if (!arr) continue;
    for (var j = 0; j < arr.length; j++) {
      var pos = arr[j];
      if (!pidSet[pos[0]]) continue;
      var xCrop = (pos[3] - cropPct.x[0]) / (cropPct.x[1] - cropPct.x[0]);
      var yCrop = (pos[4] - cropPct.y[0]) / (cropPct.y[1] - cropPct.y[0]);
      allPositions.push([pos[0], pos[1], pos[2], xCrop, yCrop]);
    }
  }

  self.postMessage({ type: "HEATMAP_POINTS_RESULT", id: id, data: allPositions });
}

// ---------------------------------------------------------------------------
// Export Positions CSV
// ---------------------------------------------------------------------------

function resolveAttrValue(pos, attr, frameKey, metaData) {
  if (attr.id === "timestamp_ms") return frameKey;
  if (attr.meta) {
    var playerId = pos[0];
    var teamId = pos[1];
    switch (attr.id) {
      case "player_number":
        var num =
          metaData && metaData.player_ids && metaData.player_ids[playerId]
            ? metaData.player_ids[playerId].number
            : undefined;
        return num != null ? num : playerId;
      case "player_name":
        return (
          (metaData && metaData.player_ids && metaData.player_ids[playerId]
            ? metaData.player_ids[playerId].name
            : "") || ""
        );
      case "team_name":
        return (
          (metaData && metaData.team_ids && metaData.team_ids[teamId]
            ? metaData.team_ids[teamId].name
            : "") || ""
        );
      default:
        return "";
    }
  }
  if (attr.csv === "team_id") {
    var tid = pos[1];
    return (
      (metaData && metaData.team_ids && metaData.team_ids[tid] ? metaData.team_ids[tid].id : tid) ||
      tid
    );
  }
  return pos[attr.id];
}

function csvEscape(val) {
  if (typeof val === "string" && (val.indexOf(",") !== -1 || val.indexOf('"') !== -1)) {
    return '"' + val.replace(/"/g, '""') + '"';
  }
  return val;
}

function handleExportPositionsCSV(id, msg) {
  var posData = msg.posData;
  var metaData = msg.metaData;
  var attrDefs = msg.attrDefs;
  var selectedTeam = msg.selectedTeam;

  var header = [];
  for (var h = 0; h < attrDefs.length; h++) header.push(attrDefs[h].csv);
  var csvHeader = header.join(",");

  var sortedKeys = Object.keys(posData).sort(function (a, b) {
    return Number(a) - Number(b);
  });
  var rows = [];

  for (var ki = 0; ki < sortedKeys.length; ki++) {
    var frameKey = sortedKeys[ki];
    var positions = posData[frameKey];
    if (!positions) continue;

    for (var pi = 0; pi < positions.length; pi++) {
      var pos = positions[pi];
      var teamMatch = Array.isArray(selectedTeam)
        ? selectedTeam.indexOf(pos[1]) !== -1
        : pos[1] === selectedTeam;
      if (!teamMatch) continue;

      var vals = [];
      for (var ai = 0; ai < attrDefs.length; ai++) {
        vals.push(csvEscape(resolveAttrValue(pos, attrDefs[ai], frameKey, metaData)));
      }
      rows.push(vals.join(","));
    }
  }

  self.postMessage({ type: "EXPORT_RESULT", id: id, data: csvHeader + "\n" + rows.join("\n") });
}

// ---------------------------------------------------------------------------
// Export Running Distance CSV
// ---------------------------------------------------------------------------

function handleExportRunningDistanceCSV(id, msg) {
  var posData = msg.posData;
  var metaData = msg.metaData;
  var attrDefs = msg.attrDefs;
  var playerIds = msg.playerIds;
  var startFrame = msg.startFrame;
  var endFrame = msg.endFrame;
  var fieldLength = msg.fieldLength;
  var fieldWidth = msg.fieldWidth;
  var selectedTeam = msg.selectedTeam;

  // Calculate distances
  var allTimes = Object.keys(posData).map(Number);
  var timeRange = [];
  for (var ti = 0; ti < allTimes.length; ti++) {
    if (allTimes[ti] >= startFrame && allTimes[ti] <= endFrame) {
      timeRange.push(allTimes[ti]);
    }
  }
  timeRange.sort(function (a, b) {
    return a - b;
  });

  var distMap = {};
  for (var fi = 0; fi < allTimes.length; fi++) {
    var players = posData[allTimes[fi]];
    if (!players) continue;
    for (var j = 0; j < players.length; j++) {
      var p = players[j];
      if (p[1] === 1) continue;
      var teamOk = !selectedTeam.length || selectedTeam.indexOf(p[1]) !== -1;
      if (!teamOk) continue;
      if (!(p[0] in distMap)) {
        distMap[p[0]] = { player_id: p[0], team_id: p[1], distance: 0 };
      }
    }
  }

  if (timeRange.length > 1) {
    for (var i = 1; i < timeRange.length; i++) {
      var tPrev = timeRange[i - 1];
      var tCurr = timeRange[i];
      var prev = posData[tPrev];
      var curr = posData[tCurr];
      if (!prev || !curr) continue;

      var prevMap = {};
      for (var k = 0; k < prev.length; k++) prevMap[prev[k][0]] = prev[k];

      for (var c = 0; c < curr.length; c++) {
        var cp = curr[c];
        if (cp[1] === 1) continue;
        var pp = prevMap[cp[0]];
        if (!pp) continue;
        if (!(cp[0] in distMap)) continue;
        var dx = (cp[3] - pp[3]) * fieldLength;
        var dy = (cp[4] - pp[4]) * fieldWidth;
        distMap[cp[0]].distance += Math.sqrt(dx * dx + dy * dy);
      }
    }
  }

  var distances = [];
  var dkeys = Object.keys(distMap);
  for (var di = 0; di < dkeys.length; di++) {
    var d = distMap[dkeys[di]];
    distances.push({
      player_id: d.player_id,
      team_id: d.team_id,
      distance: parseFloat(d.distance.toFixed(2)),
    });
  }
  distances.sort(function (a, b) {
    return a.player_id - b.player_id;
  });

  // Build CSV
  var header = [];
  for (var hi = 0; hi < attrDefs.length; hi++) header.push(attrDefs[hi].csv);
  var csvHeader = header.join(",");

  var rows = [];
  for (var ri = 0; ri < distances.length; ri++) {
    var pd = distances[ri];
    var vals = [];
    for (var ai = 0; ai < attrDefs.length; ai++) {
      var attr = attrDefs[ai];
      var val;
      switch (attr.id) {
        case "player_id":
          val =
            metaData && metaData.player_ids && metaData.player_ids[pd.player_id]
              ? metaData.player_ids[pd.player_id].number != null
                ? metaData.player_ids[pd.player_id].number
                : pd.player_id
              : pd.player_id;
          break;
        case "player_name":
          val =
            (metaData && metaData.player_ids && metaData.player_ids[pd.player_id]
              ? metaData.player_ids[pd.player_id].name
              : "") || "";
          break;
        case "team_id":
          val =
            (metaData && metaData.team_ids && metaData.team_ids[pd.team_id]
              ? metaData.team_ids[pd.team_id].id
              : pd.team_id) || pd.team_id;
          break;
        case "team_name":
          val =
            (metaData && metaData.team_ids && metaData.team_ids[pd.team_id]
              ? metaData.team_ids[pd.team_id].name
              : pd.team_id) || pd.team_id;
          break;
        case "distance":
          val = pd.distance.toFixed(2);
          break;
        default:
          val = "";
      }
      vals.push(csvEscape(val));
    }
    rows.push(vals.join(","));
  }

  self.postMessage({ type: "EXPORT_RESULT", id: id, data: csvHeader + "\n" + rows.join("\n") });
}
