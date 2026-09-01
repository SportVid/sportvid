import { watch, onBeforeUnmount } from "vue";
import Hls from "hls.js";
import { usePlayerStore } from "@/stores/player";

// The backend hands out the stored video as `<...>/<id>.tar.gz`; the playable HLS index sits
// next to it in a directory named after the same id.
export function tarGzUrlToHlsUrl(tarUrl) {
  const url = new URL(tarUrl);

  const parts = url.pathname.split("/");
  const fileName = parts.pop(); // <hash>.tar.gz
  const id = fileName.replace(/\.tar\.gz$/, "");

  parts.push(id, `${id}.m3u8`);
  url.pathname = parts.join("/");

  return url.toString();
}

// Attaches playerStore.videoUrl's HLS stream to a <video> element ref and tears the hls.js
// instance down again on unmount. Used by VideoPlayer.vue and by AnnotationView.vue --
// the latter needs its own <video> because playerStore.videoElement only exists while
// VideoPlayer.vue itself is mounted, which it isn't on the annotation route.
export function useHlsVideo(videoElementRef, { onManifestParsed } = {}) {
  let hls = null;

  watch(
    [() => usePlayerStore().videoUrl, videoElementRef],
    ([url, el]) => {
      if (!url || !el) return;

      const video = el;
      const hlsUrl = tarGzUrlToHlsUrl(url);

      if (!hlsUrl) return;

      if (hls) {
        try {
          hls.destroy();
        } catch (e) {
          console.error("Failed to destroy existing hls instance", e);
        }
        hls = null;
        try {
          video.src = "";
        } catch (e) {}
      }

      if (Hls.isSupported()) {
        hls = new Hls({
          enableWorker: true,
          lowLatencyMode: false,
          backBufferLength: 30,
          maxBufferLength: 30,
          maxMaxBufferLength: 60,
        });

        hls.loadSource(hlsUrl);
        hls.attachMedia(video);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          onManifestParsed?.();
        });
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = hlsUrl;
      }
    },
    { immediate: true }
  );

  onBeforeUnmount(() => {
    if (hls) {
      hls.destroy();
      hls = null;
    }
  });
}
