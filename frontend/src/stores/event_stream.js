import { ref } from "vue";
import { defineStore } from "pinia";
import config from "../../app.config";
import { usePluginRunStore } from "@/stores/plugin_run";
import { useVideoStore } from "@/stores/video";

// Consecutive failed connection attempts before we assume the stream is unavailable
// (proxy stripping it, backend restarting, ...) and fall back to polling.
const FALLBACK_AFTER_FAILURES = 3;
const FALLBACK_POLL_INTERVAL = 5000;

export const useEventStreamStore = defineStore("eventStream", () => {
  const connected = ref(false);
  const usingFallback = ref(false);

  let source = null;
  let failures = 0;
  let fallbackTimer = null;

  // Stores are resolved inside the handlers rather than at module scope -- same pattern
  // the other stores use here, and it keeps this file out of the import cycle.
  const handleEvent = (payload) => {
    const pluginRunStore = usePluginRunStore();
    const videoStore = useVideoStore();

    switch (payload.type) {
      case "plugin_run.update":
        pluginRunStore.applyRunEvent(payload.entry);
        break;
      case "plugin_run.deleted":
        pluginRunStore.removeRunEvent(payload.id);
        break;
      case "video.update":
        videoStore.upsert(payload.entry);
        break;
      default:
        break;
    }
  };

  const pollOnce = async () => {
    const pluginRunStore = usePluginRunStore();
    const videoStore = useVideoStore();
    // Only worth a request while something is actually in flight -- an idle app makes
    // no requests at all, even in fallback mode.
    const videosProcessing = videoStore.all.some((v) => v.processing);
    if (!pluginRunStore.pluginInProgress && !videosProcessing) return;
    await videoStore.fetchAll();
    await pluginRunStore.fetchAll({ addResults: false });
  };

  const startFallback = () => {
    if (fallbackTimer) return;
    usingFallback.value = true;
    fallbackTimer = setInterval(pollOnce, FALLBACK_POLL_INTERVAL);
  };

  const stopFallback = () => {
    if (fallbackTimer) {
      clearInterval(fallbackTimer);
      fallbackTimer = null;
    }
    usingFallback.value = false;
  };

  const connect = () => {
    if (source) return;
    if (typeof window === "undefined" || !("EventSource" in window)) {
      startFallback();
      return;
    }

    source = new EventSource(`${config.API_LOCATION}/events/stream`, {
      withCredentials: true,
    });

    source.onopen = () => {
      connected.value = true;
      failures = 0;
      stopFallback();
    };

    source.onmessage = (event) => {
      if (!event.data) return;
      try {
        handleEvent(JSON.parse(event.data));
      } catch (err) {
        console.warn("Ignoring malformed event", err);
      }
    };

    source.onerror = () => {
      connected.value = false;
      // EventSource reconnects on its own; the counter only decides when to bring the
      // polling safety net up alongside it.
      failures += 1;
      if (failures >= FALLBACK_AFTER_FAILURES) startFallback();
    };
  };

  const disconnect = () => {
    if (source) {
      source.close();
      source = null;
    }
    connected.value = false;
    failures = 0;
    stopFallback();
  };

  return { connected, usingFallback, connect, disconnect };
});
