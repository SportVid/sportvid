export function getDisplayTime(time) {
  const h = Math.floor(time / 3600_000);
  const m = Math.floor((time % 3600_000) / 60_000);
  const s = Math.floor((time % 60_000) / 1000);

  const hDisplay = h > 0 ? h + " h " : "";
  const mDisplay = m > 0 ? m + " min " : "";
  const sDisplay = s > 0 ? s + " sec" : "";

  return hDisplay + mDisplay + sDisplay;
}

// Compact "time remaining" for progress bars, from the backend's `eta_seconds`.
// Returns "" for null / non-finite / negative so callers can `v-if` it away and fall
// back to the indeterminate bar. Locale-neutral ("~3 min"); wrap with an i18n string
// for the "left / remaining" phrasing.
export function getEtaDisplay(seconds) {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return "";
  const s = Math.round(seconds);
  if (s < 60) return `~${Math.max(s, 1)} sec`;
  const m = Math.round(s / 60);
  if (m < 60) return `~${m} min`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem ? `~${h} h ${rem} min` : `~${h} h`;
}

export function getTimecode(time, numDigitsMs = 3) {
  const h = Math.floor(time / 3600_000);
  const m = Math.floor((time % 3600_000) / 60_000);
  const s = Math.floor((time % 60_000) / 1000);
  const ms = Math.round((time % 1000) * 10 ** (numDigitsMs - 3));

  const zeroPad = (num, places) => String(num).padStart(places, "0");
  if (numDigitsMs > 0) {
    return `${zeroPad(h, 2)}:${zeroPad(m, 2)}:${zeroPad(s, 2)}.${zeroPad(ms, numDigitsMs)}`;
  } else {
    return `${zeroPad(h, 2)}:${zeroPad(m, 2)}:${zeroPad(s, 2)}`;
  }
}
