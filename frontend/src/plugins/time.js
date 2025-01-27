export function getDisplayTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor((seconds % 3600) % 60);

    const hDisplay = h > 0 ? h + (h === 1 ? " h " : " h ") : "";
    const mDisplay = m > 0 ? m + (m === 1 ? " min " : " min ") : "";
    const sDisplay = s > 0 ? s + (s === 1 ? " sec" : " sec") : "";
    return hDisplay + mDisplay + sDisplay;
}

export function getTimecode(seconds, numDigitsMs = 3) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor((seconds % 3600) % 60);
    const ms = Math.round(10 ** numDigitsMs * (((seconds % 3600) % 60) % 1));

    const zeroPad = (num, places) => String(num).padStart(places, '0');
    if (numDigitsMs > 0) {
        return `${zeroPad(h, 2)}:${zeroPad(m, 2)}:${zeroPad(s, 2)}.${zeroPad(ms, numDigitsMs)}`;
    } else {
        return `${zeroPad(h, 2)}:${zeroPad(m, 2)}:${zeroPad(s, 2)}`;
    }
}


