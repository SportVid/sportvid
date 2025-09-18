<template>
  <div
    v-if="dialog"
    class="menu-item"
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
    <v-list density="compact" class="pa-0 ma-0">
      <v-list-item
        class="py-2 justify-center"
        style="height: 25px; background-color: primary; border-radius: 8px"
        @click="deleteReferenceMarker(props.marker.id)"
      >
        <v-list-item-title class="text-center">{{
          $t("calibration_asset.marker.delete_single_ref_marker")
        }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </div>
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
</style>
