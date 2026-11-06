import { ref } from "vue";

/**
 * Client-side tracking for a browser -> server file upload.
 *
 * Exposes a reactive percentage (0..100) and a smoothed estimate of the seconds still
 * remaining (null until it's meaningful, and again once the bytes are all sent and we
 * are just waiting on the server's response). Feed `onUploadProgress` straight to
 * axios; call `start()` right before the request and `finish()` in `finally`.
 */
export function useUploadTracker() {
  const isUploading = ref(false);
  const progress = ref(0);
  const etaSeconds = ref(null);

  let rate = 0; // bytes/sec, exponential moving average
  let lastLoaded = 0;
  let lastT = 0;

  const start = () => {
    isUploading.value = true;
    progress.value = 0;
    etaSeconds.value = null;
    rate = 0;
    lastLoaded = 0;
    lastT = performance.now();
  };

  const finish = () => {
    isUploading.value = false;
    progress.value = 0;
    etaSeconds.value = null;
  };

  const onUploadProgress = (event) => {
    const total =
      event.total ||
      (event.lengthComputable ? event.total : null) ||
      Number(event.target?.getResponseHeader?.("content-length")) ||
      Number(event.target?.getResponseHeader?.("x-decompressed-content-length")) ||
      null;
    if (!total) return;

    const loaded = event.loaded || 0;
    progress.value = Math.min(100, Math.round((loaded * 100) / total));

    const now = performance.now();
    const dt = (now - lastT) / 1000;
    const db = loaded - lastLoaded;
    // Only learn from a real chunk of elapsed time so a burst of events doesn't spike
    // the rate; 1.0 is handled below regardless.
    if (dt >= 0.15 && db > 0) {
      const inst = db / dt;
      rate = rate > 0 ? 0.3 * inst + 0.7 * rate : inst;
      lastT = now;
      lastLoaded = loaded;
    }

    if (loaded >= total) {
      etaSeconds.value = null; // all sent -- now waiting on the server
    } else if (rate > 0) {
      etaSeconds.value = (total - loaded) / rate;
    }
  };

  return { isUploading, progress, etaSeconds, start, finish, onUploadProgress };
}
