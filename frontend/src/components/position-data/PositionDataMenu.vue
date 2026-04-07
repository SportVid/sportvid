<template>
  <div style="height: 60vh" data-tour="position-data-menu">
    <v-col>
      <v-row
        class="text-h6 text-grey font-weight-light mx-16 px-10 mt-8"
        style="
          align-items: center;
          justify-content: center;
          text-align: center;
          line-height: 1.5;
          height: 30vh;
        "
        v-html="$t('position_data.not_selected')"
      />
      <v-row style="justify-content: center">
        <v-btn data-tour="posdata-manual-upload-open" @click="showModalPositionDataUpload = true">{{
          $t("position_data.display_settings.position_data.upload")
        }}</v-btn>
      </v-row>
      <v-row style="justify-content: center" class="mt-8">
        <v-btn @click="showModalPositionDataSelect = true">{{
          $t("position_data.display_settings.position_data.select")
        }}</v-btn>
        <ModalPositionDataSelect
          v-if="showModalPositionDataSelect"
          v-model="showModalPositionDataSelect"
        />
        <ModalPositionDataUpload
          v-if="showModalPositionDataUpload"
          v-model="showModalPositionDataUpload"
        />
      </v-row>
    </v-col>
  </div>
</template>

<script setup>
import { ref } from "vue";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";

const showModalPositionDataUpload = ref(false);
const showModalPositionDataSelect = ref(false);
</script>
