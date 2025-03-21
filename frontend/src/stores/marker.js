import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useVideoStore } from "./video";
import { useCompAreaStore } from "./comp_area";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export const useMarkerStore = defineStore("marker", () => {
  const videoStore = useVideoStore();
  const compAreaStore = useCompAreaStore();

  const showReferenceMarker = ref(false);
  const hoveredReferenceMarker = ref(null);
  const isAddingMarker = ref(false);
  const showBoundingBox = ref(false);

  const marker = ref([
    {
      name: "Top-left",
      id: "1",
      active: false,
      compAreaCoordsRel: { x: 0, y: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Top-right",
      id: "2",
      active: false,
      compAreaCoordsRel: { x: 0, y: 1 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Kick-off",
      id: "3",
      active: false,
      compAreaCoordsRel: { x: 0.5, y: 0.5 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Bottom-left",
      id: "4",
      active: false,
      compAreaCoordsRel: { x: 1, y: 0 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
    {
      name: "Bottom-right",
      id: "5",
      active: false,
      compAreaCoordsRel: { x: 1, y: 1 },
      videoCoordsRel: { x: null, y: null, z: null },
    },
  ]);

  const filteredMarker = computed(() => {
    return marker.value.filter(
      (marker) => marker.compAreaCoordsRel.x !== null && marker.compAreaCoordsRel.y !== null
    );
  });

  const filteredReferenceMarker = computed(() => {
    return marker.value.filter(
      (marker) => marker.videoCoordsRel.x !== null && marker.videoCoordsRel.y !== null
    );
  });

  const isAnyMarkerActive = computed(() => marker.value.some((marker) => marker.active));

  const toggleMarker = (event, id) => {
    event.stopPropagation();

    marker.value = marker.value.map((marker) => ({
      ...marker,
      active: marker.id === id ? !marker.active : false,
    }));
  };

  const addMarker = () => {
    if (!isAddingMarker.value) {
      isAddingMarker.value = true;

      const customMarkerCount = marker.value.filter((m) =>
        m.name.startsWith("Custom-marker")
      ).length;
      const newMarker = {
        name: `Custom-marker-${customMarkerCount + 1}`,
        id: marker.value.length + 1,
        active: false,
        compAreaCoordsRel: { x: null, y: null, z: null },
        videoCoordsRel: { x: null, y: null, z: null },
      };

      marker.value.push(newMarker);
    }
  };

  const setMarker = (event) => {
    if (isAddingMarker.value) {
      const lastMarker = marker.value[marker.value.length - 1];
      if (lastMarker) {
        lastMarker.compAreaCoordsRel = {
          x:
            (event.clientX -
              (compAreaStore.compAreaSize.left +
                ((1 - 2698 / 2910) / 2) * compAreaStore.compAreaSize.width)) /
            (compAreaStore.compAreaSize.width * (2698 / 2910)),
          y:
            (event.clientY -
              (compAreaStore.compAreaSize.top +
                ((1 - 1794 / 2010) / 2) * compAreaStore.compAreaSize.height)) /
            (compAreaStore.compAreaSize.height * (1794 / 2010)),
          x:
            (event.clientX -
              (compAreaStore.compAreaSize.left +
                ((1 - 2698 / 2910) / 2) * compAreaStore.compAreaSize.width)) /
            (compAreaStore.compAreaSize.width * (2698 / 2910)),
          y:
            (event.clientY -
              (compAreaStore.compAreaSize.top +
                ((1 - 1794 / 2010) / 2) * compAreaStore.compAreaSize.height)) /
            (compAreaStore.compAreaSize.height * (1794 / 2010)),
        };
      }

      isAddingMarker.value = false;
    }
  };

  const deleteMarker = (id) => {
    marker.value = marker.value.filter((m) => m.id !== id);
  };

  const setReferenceMarker = (event) => {
    const activeMarker = marker.value.find((marker) => marker.active);
    if (!activeMarker) return;

    activeMarker.videoCoordsRel = {
      x: (event.clientX - videoStore.videoSize.left) / videoStore.videoSize.width,
      y: (event.clientY - videoStore.videoSize.top) / videoStore.videoSize.height,
    };

    activeMarker.active = false;
  };

  const viewReferenceMarker = () => {
    showReferenceMarker.value = !showReferenceMarker.value;
  };

  const viewBoundingBox = () => {
    showBoundingBox.value = !showBoundingBox.value;
  };

  const positionsNested = ref(
    Array.from({ length: 100 }, () =>
      Array.from({ length: 20 }, (_, playerIndex) => {
        const isTeamA = playerIndex < 10;

        return {
          bbox_top: Math.random() * 0.8 + 0.1, // x
          bbox_left: Math.random() * 0.6 + (isTeamA ? 0.1 : 0.3), // y
          bbox_width: 0.05, // w
          bbox_height: 0.1, // h
          team: isTeamA ? "blue" : "red", // will be in class BboxDataTeam
          image_id: 0, // image_id (= frame)
          time: 0, // image_id / fps
          ref_id: 1,
          det_score: 1.0,
        };
      })
    )
  );

  const positionsFlat = ref(
    Array.from({ length: 100 * 20 }, (_, index) => {
      const image_id = Math.floor(index / 20); // Frame (0-99)
      const ref_id = (index % 20) + 1; // Spieler-ID (1-20)
      const isTeamA = ref_id <= 10; // Team-Zuordnung

      return {
        bbox_top: Math.random() * 0.8 + 0.1, // y
        bbox_left: Math.random() * 0.6 + (isTeamA ? 0.1 : 0.3), // x
        bbox_width: 0.05, // w
        bbox_height: 0.1, // h
        team: isTeamA ? "blue" : "red", // Team-Zuordnung
        image_id: image_id, // Frame-Nummer
        time: image_id / 1, // Angenommene FPS von 30
        ref_id: ref_id, // Spieler-Referenz-ID (1-20)
        det_score: 1.0, // Score-Wert
      };
    })
  );

  const showSpaceControl = ref(false);
  const viewSpaceControl = () => {
    showSpaceControl.value = !showSpaceControl.value;
    showEffectivePlayingSpace.value = false;
  };

  const showEffectivePlayingSpace = ref(false);
  const viewEffectivePlayingSpace = () => {
    showEffectivePlayingSpace.value = !showEffectivePlayingSpace.value;
    showSpaceControl.value = false;
  };

  const annotations = ref({});

  const saveAnnotation = (name) => {
    if (!name) return;
    annotations.value[name] = [...marker.value];
    console.log(annotations.value);
    localStorage.setItem("annotations", JSON.stringify(annotations.value));
  };

  //TODO: store annotations in db
  // requires video_id, dict/list source / tgt point
  // const create = async ({ name, color, categoryId, videoId = null }) => {
  //   if (isLoading.value) return;
  //   isLoading.value = true;

  //   const params = { # TODO definitions of params,
  // TODO create CalibrationAssets class backend/backend/models.py and link in backend/backend/urls.py
  // TODO: create new view for CalibrationAssets DB I/O in backend/backend/views/?.py (c.f.annotation.py)
  //     name,
  //     color,
  //     category_id: categoryId || undefined,
  //     video_id: videoId || usePlayerStore().videoId,
  //   };

  // TODO: implement point_correspeondences/<create,get> etc.
  //   try {
  //     const res = await axios.post(`${config.API_LOCATION}/point_correspondences/create`, params);
  //     if (res.data.status === "ok") {
  //       addToStore([res.data.entry]);
  //       return res.data.entry.id;
  //     }
  //   } finally {
  //     isLoading.value = false;
  //   }
  // };

  const loadAnnotation = (name) => {
    if (annotations.value[name]) {
      marker.value = [...annotations.value[name]];
    }
  };

  const loadFromLocalStorage = () => {
    const storedAnnotations = JSON.parse(localStorage.getItem("annotations"));
    if (storedAnnotations) annotations.value = storedAnnotations;
  };

  const deleteAnnotation = (name) => {
    if (!annotations.value[name]) return;
    delete annotations.value[name];
    localStorage.setItem("annotations", JSON.stringify(annotations.value));
  };

  return {
    marker,
    filteredMarker,
    filteredReferenceMarker,
    toggleMarker,
    isAnyMarkerActive,
    isAddingMarker,
    addMarker,
    setMarker,
    deleteMarker,
    setReferenceMarker,
    showReferenceMarker,
    viewReferenceMarker,
    hoveredReferenceMarker,
    showBoundingBox,
    viewBoundingBox,
    showSpaceControl,
    viewSpaceControl,
    showEffectivePlayingSpace,
    viewEffectivePlayingSpace,
    annotations,
    saveAnnotation,
    loadAnnotation,
    loadFromLocalStorage,
    deleteAnnotation,
    positionsNested,
    positionsFlat,
  };
});
