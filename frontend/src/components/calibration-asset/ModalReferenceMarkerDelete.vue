<template>
  <!-- <div
    v-if="dialog"
    v-click-outside="() => (dialog = false)"
    :style="{
      position: 'absolute',
      transform: 'translateX(-50%)',
      top:
        props.marker.compAreaCoordsRel.y *
          (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
        ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
        15 +
        'px',
      left:
        props.marker.compAreaCoordsRel.x *
          (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
        ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
        'px',
    }"
  >
    <v-list density="compact" class="pa-0 menu-item" style="border-radius: 10px">
      <v-list-item
        style="color: white; background-color: rgb(var(--v-theme-primary))"
        @click="deleteReferenceMarker(props.marker.id)"
      >
        <v-list-item-title class="text-center">{{
          $t("calibration_asset.marker.delete_single_ref_marker")
        }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </div> -->

  <v-btn
    v-if="dialog"
    v-click-outside="() => (dialog = false)"
    color="red"
    icon="mdi-close"
    variant="plain"
    density="compact"
    @click="deleteReferenceMarker(props.marker.id)"
    class="delete-marker-position"
    :style="{
      position: 'absolute',
      transform: 'translate(-50%, -50%)',
      top:
        props.marker.compAreaCoordsRel.y *
          (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
        ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
        'px',
      left:
        props.marker.compAreaCoordsRel.x *
          (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
        ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
        'px',
    }"
  />
</template>

<script setup>
import { ref, watch } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

const topViewStore = useTopViewStore();
const calibrationAssetStore = useCalibrationAssetStore();

const props = defineProps({
  marker: { type: Object, required: true },
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:modelValue"]);

const dialog = ref(props.modelValue);
watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
  }
);
watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      dialog.value = true;
    }
  }
);

const deleteReferenceMarker = (id) => {
  calibrationAssetStore.deleteReferenceMarker(id);
  dialog.value = false;
};
</script>

<style scoped>
.menu-item {
  cursor: pointer;
}

.menu-item .v-list-item-title {
  font-size: 10px;
}

.delete-marker-position .v-icon {
  transform: scale(0.7);
}

.delete-marker-position:hover {
  border: 1px red solid;
}
</style>
