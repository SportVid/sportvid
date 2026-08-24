import { ref, watch } from "vue";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";

// Shared "create-calibration" wiring for any host that embeds Parameters.vue's
// "select_calibration" field (calibration_static_dlt today, ModalPositionDataCreate.vue's
// calibration section too): opens ModalCalibrationAssetCreate, and once a fresh asset comes
// out of it, closes the host dialog and drops the user into the full calibration editor
// (calibrationAssetStore.calibrationMode). Extracted out of ModalPluginRun.vue so it isn't
// duplicated per host.
export function useCalibrationCreateFlow(dialog) {
  const calibrationAssetStore = useCalibrationAssetStore();

  const showCalibrationCreate = ref(false);
  const onCreateCalibration = () => {
    showCalibrationCreate.value = true;
  };
  const onSelectCalibration = () => {
    dialog.value = false;
    calibrationAssetStore.calibrationMode = true;
  };
  watch(showCalibrationCreate, (newVal, oldVal) => {
    if (oldVal && !newVal && calibrationAssetStore.calibrationAssetObjects.length > 0) {
      dialog.value = false;
      calibrationAssetStore.calibrationMode = true;
    }
  });

  return { showCalibrationCreate, onCreateCalibration, onSelectCalibration };
}
