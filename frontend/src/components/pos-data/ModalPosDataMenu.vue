<template>
  <div style="height: 60vh">
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
        v-html="$t('pos_data.not_selected')"
      />
      <v-row style="justify-content: center">
        <v-btn @click="showModalPosDataUpload = true">{{
          $t("pos_data.display_settings.pos_data.upload")
        }}</v-btn>
      </v-row>
      <v-row style="justify-content: center" class="mt-8">
        <v-btn @click="showModalPosDataSelect = true">{{
          $t("pos_data.display_settings.pos_data.select")
        }}</v-btn>
        <ModalPosDataSelect v-if="showModalPosDataSelect" v-model="showModalPosDataSelect" />
        <ModalPosDataUpload v-if="showModalPosDataUpload" v-model="showModalPosDataUpload" />
      </v-row>
    </v-col>
  </div>
</template>

<script setup>
import { ref } from "vue";
import ModalPosDataUpload from "@/components/pos-data/ModalPosDataUpload.vue";
import ModalPosDataSelect from "@/components/pos-data/ModalPosDataSelect.vue";

const showModalPosDataUpload = ref(false);
const showModalPosDataSelect = ref(false);
</script>
