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
        v-html="notSelectedText"
      />
      <v-row v-if="canWrite" style="justify-content: center">
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
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";

const { t } = useI18n();
const playerStore = usePlayerStore();
const userStore = useUserStore();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const notSelectedText = computed(() => {
  const full = t("position_data.not_selected");
  return canWrite.value ? full : full.split("<br>")[0];
});

const showModalPositionDataUpload = ref(false);
const showModalPositionDataSelect = ref(false);
</script>
