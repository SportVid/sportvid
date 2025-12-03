<template>
  <div style="height: 60vh" data-tour="calibration-asset-menu">
    <v-col>
      <v-row
        class="text-h6 text-grey font-weight-light mx-16 px-10 mt-8"
        style="
          align-items: center;
          justify-content: center;
          text-align: center;
          line-height: 1.5;
          height: 25vh;
        "
        v-html="$t('calibration_asset.not_selected')"
      />
      <v-row style="justify-content: center">
        <v-btn @click="showModalCalibrationAssetCreate = true">{{
          $t("calibration_asset.create")
        }}</v-btn>
      </v-row>
      <v-row style="justify-content: center" class="mt-8">
        <v-btn @click="showModalCalibrationAssetSelect = true">{{
          $t("calibration_asset.select")
        }}</v-btn>
        <ModalCalibrationAssetCreate
          v-if="showModalCalibrationAssetCreate"
          v-model="showModalCalibrationAssetCreate"
        />
        <ModalCalibrationAssetSelect
          v-if="showModalCalibrationAssetSelect"
          v-model="showModalCalibrationAssetSelect"
        />
      </v-row>
    </v-col>
  </div>
</template>

<script setup>
import { ref } from "vue";
import ModalCalibrationAssetCreate from "@/components/tab-window/ModalCalibrationAssetCreate.vue";
import ModalCalibrationAssetSelect from "@/components/calibration-asset/ModalCalibrationAssetSelect.vue";

const showModalCalibrationAssetCreate = ref(false);
const showModalCalibrationAssetSelect = ref(false);
</script>
