export function getDisplayTime(time) {
  const h = Math.floor(time / 3600_000);
  const m = Math.floor((time % 3600_000) / 60_000);
  const s = Math.floor((time % 60_000) / 1000);

  const hDisplay = h > 0 ? h + " h " : "";
  const mDisplay = m > 0 ? m + " min " : "";
  const sDisplay = s > 0 ? s + " sec" : "";

  return hDisplay + mDisplay + sDisplay;
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
