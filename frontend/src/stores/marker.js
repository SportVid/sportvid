import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";
import { useVideoStore } from "./video";
import { useCompAreaStore } from "./comp_area";
import { usePlayerStore } from "@/stores/player";
import { usePluginRunStore } from "@/stores/plugin_run";
import { usePluginRunResultStore } from "@/stores/plugin_run_result";

export const useMarkerStore = defineStore("marker", () => {
  const videoStore = useVideoStore();
  const compAreaStore = useCompAreaStore();
  const playerStore = usePlayerStore();

  const showReferenceMarker = ref(false);
  const hoveredReferenceMarker = ref(null);
  const isAddingMarker = ref(false);

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

  const annotations = ref({});

  const saveAnnotation = (name) => {
    if (!name) return;
    annotations.value[name] = [...marker.value];
    localStorage.setItem("annotations", JSON.stringify(annotations.value));
  };

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

  const isLoading = ref(false);
  //TODO: store annotations in db
  // requires video_id, dict/list source / tgt point
  const create = async ({ name }) => {
    if (isLoading.value || !name) return;
    isLoading.value = true;
    const params = {
      // # TODO definitions of params,
      // TODO create CalibrationAssets class backend/backend/models.py and link in backend/backend/urls.py
      // TODO: create new view for CalibrationAssets DB I/O in backend/backend/views/?.py (c.f.annotation.py)
      name,
      marker_data: [...marker.value],
      video_id: playerStore.videoId,
    };
    // TODO: implement point_correspondences/<create,get> etc.
    try {
      console.log(params);
      // const res = await axios.post(`${config.API_LOCATION}/point_correspondences/create`, params);
      // if (res.data.status === "ok") {
      //   addToStore([res.data.entry]);
      //   return res.data.entry.id;
      // }
    } finally {
      isLoading.value = false;
    }
  };

  const saveAnno = async (name) => {
    const id = await create({ name });
    if (id) {
      console.log(`Annotation mit ID ${id} gespeichert`);
    }
  };

  const clearStore = () => {
    Object.keys(annotations).forEach((key) => {
      delete annotations[key];
    });
  };

  const updateInStore = (newAnnotations) => {
    newAnnotations.forEach((e) => {
      annotations[e.id] = e;
    });
  };

  const addToStore = (newAnnotations) => {
    newAnnotations.forEach((e) => {
      annotations[e.id] = e;
    });
  };

  const updateStore = (newAnnotations) => {
    newAnnotations.forEach((e) => {
      if (!(e.id in annotations)) {
        annotations[e.id] = e;
      }
    });
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
    annotations,
    saveAnnotation,
    loadAnnotation,
    loadFromLocalStorage,
    deleteAnnotation,
    create,
    isLoading,
    clearStore,
    updateInStore,
    addToStore,
    updateStore,
    saveAnno,
  };
});
