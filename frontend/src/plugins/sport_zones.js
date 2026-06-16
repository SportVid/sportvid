// ─── Handball ────────────────────────────────────────────────────────────────
// Field is 2:1 (length:width). Coordinates normalized [0,1].
// Goal posts at y=0.425 / y=0.575. Corner point x = 0.425/2 = 0.2125.

const HB_GOAL_YL = 0.425; // top goal post
const HB_GOAL_YH = 0.575; // bottom goal post
const HB_CORNER_X = HB_GOAL_YL / 2; // 0.2125 – diagonal reaches here at y=0/1

// x-coordinate of the wing diagonal at a given py (valid for py < HB_GOAL_YL)
function _hbDiagTop(py) {
  return (HB_GOAL_YL - py) / 2;
}

// x-coordinate of the wing diagonal at a given py (valid for py > HB_GOAL_YH)
function _hbDiagBot(py) {
  return (py - HB_GOAL_YH) / 2;
}

function _hbContainLeftHalf(zoneId, px, py) {
  switch (zoneId) {
    case 0: // top wing triangle
      return py < HB_GOAL_YL && px < _hbDiagTop(py);
    case 1: // top side zone (diagonal edge + rect to midline)
      return py < HB_GOAL_YL && px >= _hbDiagTop(py);
    case 2: // center zone (rect between posts to midline)
      return py >= HB_GOAL_YL && py <= HB_GOAL_YH;
    case 3: // bottom side zone
      return py > HB_GOAL_YH && px >= _hbDiagBot(py);
    case 4: // bottom wing triangle
      return py > HB_GOAL_YH && px < _hbDiagBot(py);
    default:
      return false;
  }
}

function _hbPolyLeftHalf(zoneId) {
  switch (zoneId) {
    case 0: // top wing triangle
      return [[0, 0], [HB_CORNER_X, 0], [0, HB_GOAL_YL]];
    case 1: // top side zone
      return [[HB_CORNER_X, 0], [0.5, 0], [0.5, HB_GOAL_YL], [0, HB_GOAL_YL]];
    case 2: // center rectangle
      return [[0, HB_GOAL_YL], [0.5, HB_GOAL_YL], [0.5, HB_GOAL_YH], [0, HB_GOAL_YH]];
    case 3: // bottom side zone
      return [[0, HB_GOAL_YH], [0.5, HB_GOAL_YH], [0.5, 1], [HB_CORNER_X, 1]];
    case 4: // bottom wing triangle
      return [[HB_CORNER_X, 1], [0, 1], [0, HB_GOAL_YH]];
    default:
      return [];
  }
}

// ─── Basketball ──────────────────────────────────────────────────────────────
// Field 28 m × 15 m, coordinates normalised [0,1] with (0,0) = bottom-left.
// Constants taken from calibration asset markers / segments.

const BB_BKT = 1.575 / 28;  // basket x from baseline ≈ 0.05625
const BB_PAINT_X = 0.2025;  // key far-edge x  (key-left-top-right)
const BB_PAINT_YL = 0.34;   // key bottom y     (key-left-bottom-*)
const BB_PAINT_YH = 0.66;   // key top y        (key-left-top-*)
const BB_COR_YL = 0.06;     // 3-pt straight segment bottom y
const BB_COR_YH = 0.94;     // 3-pt straight segment top y
const BB_3PT_X = 0.15;      // x where 3-pt straight segment meets the arc
// BB_R2 calibrated so the arc passes exactly through (BB_3PT_X, BB_COR_YH/L)
const BB_R2 =
  (BB_3PT_X - BB_BKT) ** 2 * 28 ** 2 + (BB_COR_YH - 0.5) ** 2 * 15 ** 2;

// y-coordinates where the diagonal (key-top-right → midline-top-corner) and its
// mirror cross the 3-pt arc — used to divide inside/outside-arc zones cleanly.
const { BB_DIAG_TOP_Y, BB_DIAG_BOT_Y } = (() => {
  const slope = (1 - BB_PAINT_YH) / (0.5 - BB_PAINT_X);
  const p = 15 * ((BB_PAINT_YH - 0.5) + slope * (BB_BKT - BB_PAINT_X));
  const q = (15 * slope) / 28;
  const A = 1 + q * q;
  const B = 2 * p * q;
  const C = p * p - BB_R2;
  const u = (-B + Math.sqrt(B * B - 4 * A * C)) / (2 * A);
  const xi = BB_BKT + u / 28;
  const yi = BB_PAINT_YH + slope * (xi - BB_PAINT_X);
  return { BB_DIAG_TOP_Y: yi, BB_DIAG_BOT_Y: 1 - yi };
})();

function _bbArcX(py) {
  const dy = (py - 0.5) * 15;
  const r2 = BB_R2 - dy * dy;
  return r2 > 0 ? BB_BKT + Math.sqrt(r2) / 28 : null;
}

function _bbArcSeg(y0, y1, steps) {
  steps = steps || 16;
  const pts = [];
  for (let i = 0; i <= steps; i++) {
    const py = y0 + (y1 - y0) * (i / steps);
    const x = _bbArcX(py);
    if (x !== null) pts.push([x, py]);
  }
  return pts;
}

function _bbInArc(px, py) {
  const dx = (px - BB_BKT) * 28;
  const dy = (py - 0.5) * 15;
  return dx * dx + dy * dy < BB_R2;
}

function _bbAboveTopDiag(px, py) {
  return py > BB_PAINT_YH + ((1 - BB_PAINT_YH) / (0.5 - BB_PAINT_X)) * (px - BB_PAINT_X);
}
function _bbBelowBotDiag(px, py) {
  return py < BB_PAINT_YL + ((0 - BB_PAINT_YL) / (0.5 - BB_PAINT_X)) * (px - BB_PAINT_X);
}

// Zones (left half, px ≤ 0.5):
//  0 – key rectangle
//  1 – corner top   (outside 3-pt straight, top sideline side)
//  2 – corner bottom
//  3 – inside arc, top   (above top diagonal)
//  4 – inside arc, center (between diagonals)
//  5 – inside arc, bottom (below bottom diagonal)
//  6 – outside arc, top   (above top diagonal, non-corner)
//  7 – outside arc, center (between diagonals)
//  8 – outside arc, bottom (below bottom diagonal, non-corner)
function _bbContainLeftHalf(zoneId, px, py) {
  const inKey = px < BB_PAINT_X && py >= BB_PAINT_YL && py <= BB_PAINT_YH;
  const inCornerTop = py >= BB_COR_YH && px <= BB_3PT_X;
  const inCornerBot = py <= BB_COR_YL && px <= BB_3PT_X;
  const inArc = _bbInArc(px, py);
  const aboveTop = _bbAboveTopDiag(px, py);
  const belowBot = _bbBelowBotDiag(px, py);
  switch (zoneId) {
    case 0: return inKey;
    case 1: return inCornerTop;
    case 2: return inCornerBot;
    case 3: return !inCornerTop && inArc && !inKey && aboveTop;
    case 4: return !inCornerTop && !inCornerBot && inArc && !inKey && !aboveTop && !belowBot;
    case 5: return !inCornerBot && inArc && !inKey && belowBot;
    case 6: return !inCornerTop && !inArc && aboveTop;
    case 7: return !inCornerTop && !inCornerBot && !inArc && !aboveTop && !belowBot;
    case 8: return !inCornerBot && !inArc && belowBot;
    default: return false;
  }
}

function _bbPolyLeftHalf(zoneId) {
  switch (zoneId) {
    case 0:
      return [[0, BB_PAINT_YL], [BB_PAINT_X, BB_PAINT_YL], [BB_PAINT_X, BB_PAINT_YH], [0, BB_PAINT_YH]];
    case 1:
      return [[0, BB_COR_YH], [BB_3PT_X, BB_COR_YH], [BB_3PT_X, 1], [0, 1]];
    case 2:
      return [[0, 0], [BB_3PT_X, 0], [BB_3PT_X, BB_COR_YL], [0, BB_COR_YL]];
    case 3:
      // baseline → key top-right → arc (diag intersect → 3-pt corner) → baseline top
      return [
        [0, BB_PAINT_YH],
        [BB_PAINT_X, BB_PAINT_YH],
        ..._bbArcSeg(BB_DIAG_TOP_Y, BB_COR_YH),
        [0, BB_COR_YH],
      ];
    case 4:
      // key top-right → arc (top diag intersect → bottom diag intersect) → key bottom-right
      return [
        [BB_PAINT_X, BB_PAINT_YH],
        ..._bbArcSeg(BB_DIAG_TOP_Y, BB_DIAG_BOT_Y),
        [BB_PAINT_X, BB_PAINT_YL],
      ];
    case 5:
      // baseline bottom → arc (3-pt corner → bottom diag intersect) → key bottom-right → baseline
      return [
        [0, BB_COR_YL],
        ..._bbArcSeg(BB_COR_YL, BB_DIAG_BOT_Y),
        [BB_PAINT_X, BB_PAINT_YL],
        [0, BB_PAINT_YL],
      ];
    case 6:
      // arc (3-pt corner → top diag intersect) → midline top corner → corner zone edge
      return [
        ..._bbArcSeg(BB_COR_YH, BB_DIAG_TOP_Y),
        [0.5, 1],
        [BB_3PT_X, 1],
      ];
    case 7:
      // arc (top diag intersect → bottom diag intersect) → midline bottom → midline top
      return [
        ..._bbArcSeg(BB_DIAG_TOP_Y, BB_DIAG_BOT_Y),
        [0.5, 0],
        [0.5, 1],
      ];
    case 8:
      // arc (bottom diag intersect → 3-pt corner) → corner zone edge → midline bottom
      return [
        ..._bbArcSeg(BB_DIAG_BOT_Y, BB_COR_YL),
        [BB_3PT_X, 0],
        [0.5, 0],
      ];
    default:
      return [];
  }
}

// ─── Public API ──────────────────────────────────────────────────────────────

export const HANDBALL_ZONES = [
  { id: 0, nameKey: "sports.handball.zones.top_wing" },
  { id: 1, nameKey: "sports.handball.zones.top_side" },
  { id: 2, nameKey: "sports.handball.zones.center" },
  { id: 3, nameKey: "sports.handball.zones.bottom_side" },
  { id: 4, nameKey: "sports.handball.zones.bottom_wing" },
];

export const BASKETBALL_ZONES = [
  { id: 0, nameKey: "sports.basketball.zones.key" },
  { id: 1, nameKey: "sports.basketball.zones.corner_top" },
  { id: 2, nameKey: "sports.basketball.zones.corner_bottom" },
  { id: 3, nameKey: "sports.basketball.zones.mid_top" },
  { id: 4, nameKey: "sports.basketball.zones.mid_center" },
  { id: 5, nameKey: "sports.basketball.zones.mid_bottom" },
  { id: 6, nameKey: "sports.basketball.zones.three_top" },
  { id: 7, nameKey: "sports.basketball.zones.three_center" },
  { id: 8, nameKey: "sports.basketball.zones.three_bottom" },
];

/**
 * Returns true if (px, py) belongs to zone `zoneId` of `sportKey`.
 * If `half` is 0 only the left field half (px≤0.5) is tested,
 * if 1 only the right half — if undefined both halves are tested.
 */
export function isInSportZone(sportKey, zoneId, px, py, half = undefined) {
  const isLeft = px <= 0.5;
  if (half === 0 && !isLeft) return false;
  if (half === 1 && isLeft) return false;
  const testPx = isLeft ? px : 1 - px;
  if (sportKey === "handball") return _hbContainLeftHalf(zoneId, testPx, py);
  if (sportKey === "basketball") return _bbContainLeftHalf(zoneId, testPx, py);
  return false;
}

/**
 * Returns [leftPoly, rightPoly] — both halves of the zone.
 */
export function getSportZonePolygons(sportKey, zoneId) {
  let leftPoly, rightPolyFn;
  if (sportKey === "handball") {
    leftPoly = _hbPolyLeftHalf(zoneId);
    rightPolyFn = (pts) => pts.map(([x, y]) => [1 - x, y]);
  } else if (sportKey === "basketball") {
    leftPoly = _bbPolyLeftHalf(zoneId);
    rightPolyFn = (pts) => pts.map(([x, y]) => [1 - x, y]);
  } else {
    return [];
  }
  if (!leftPoly.length) return [];
  return [leftPoly, rightPolyFn(leftPoly)];
}

/**
 * Returns the polygon for a single field half.
 * half=0 → left (x≤0.5), half=1 → right (x>0.5).
 */
export function getSportZonePolygon(sportKey, zoneId, half) {
  const polys = getSportZonePolygons(sportKey, zoneId);
  return polys[half] ?? [];
}

/**
 * Returns the structural boundary lines [[x1,y1],[x2,y2]] to draw
 * as a zone overlay on the full field (not full polygon outlines).
 */
export function getSportFieldLines(sportKey) {
  if (sportKey === "handball") {
    return [
      [[0.5, 0], [0.5, 1]],
      [[0, HB_GOAL_YL], [HB_CORNER_X, 0]],
      [[0, HB_GOAL_YH], [HB_CORNER_X, 1]],
      [[0, HB_GOAL_YL], [1, HB_GOAL_YL]],
      [[0, HB_GOAL_YH], [1, HB_GOAL_YH]],
      [[1, HB_GOAL_YL], [1 - HB_CORNER_X, 0]],
      [[1, HB_GOAL_YH], [1 - HB_CORNER_X, 1]],
    ];
  }
  return [];
}

/**
 * Build the default "all zones selected" array for a given sport.
 * Handball zones include a `half` field (0=left, 1=right) so each
 * field half can be toggled independently.
 */
export function allSportZones(sportKey) {
  if (sportKey === "handball") {
    const zones = [];
    for (let h = 0; h < 2; h++)
      for (let i = 0; i < 5; i++)
        zones.push({ sportZone: true, sportKey, zoneId: i, half: h });
    return zones;
  }
  if (sportKey === "basketball") {
    const zones = [];
    for (let h = 0; h < 2; h++)
      for (let i = 0; i < 9; i++)
        zones.push({ sportZone: true, sportKey, zoneId: i, half: h });
    return zones;
  }
  return [];
}
