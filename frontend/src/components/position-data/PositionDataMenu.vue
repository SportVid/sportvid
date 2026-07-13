<template>
  <div style="min-height: 60vh" data-tour="position-data-menu">
    <v-col>
      <v-row
        v-if="!hasAvailablePositionData"
        class="text-h6 text-grey font-weight-light mx-16 px-10 mt-2"
        style="align-items: center; justify-content: center; text-align: center; line-height: 1.5"
      >
        {{ $t("position_data.not_selected") }}
      </v-row>

      <template v-if="canWrite">
        <v-row style="justify-content: center" class="mt-6">
          <v-col cols="10">
            <v-sheet border rounded class="pa-4 bg-transparent">
              <v-row
                class="text-caption text-grey text-uppercase mt-4 mb-2"
                style="justify-content: center"
              >
                {{ $t("position_data.generate.cv_heading") }}
              </v-row>
              <v-row style="justify-content: center" class="mt-1 ga-4">
                <v-btn data-tour="posdata-generate-bytetrack" @click="showBytetrackModal = true">
                  {{ $t("position_data.generate.bytetrack") }}
                </v-btn>

                <v-btn data-tour="posdata-generate-dlt" @click="showDltModal = true">
                  {{ $t("position_data.generate.dlt") }}
                </v-btn>
              </v-row>

              <v-row style="justify-content: center; align-items: center" class="mt-4 mb-n2">
                <v-col cols="4" class="d-flex align-center">
                  <v-divider />
                </v-col>
                <v-col cols="auto" class="text-grey px-2">{{
                  $t("position_data.generate.or")
                }}</v-col>
                <v-col cols="4" class="d-flex align-center">
                  <v-divider />
                </v-col>
              </v-row>

              <v-row
                class="text-caption text-grey text-uppercase mb-2"
                style="justify-content: center"
              >
                {{ $t("position_data.generate.upload_heading") }}
              </v-row>
              <v-row style="justify-content: center" class="mt-1 mb-4">
                <v-btn
                  data-tour="posdata-manual-upload-open"
                  @click="showModalPositionDataUpload = true"
                  >{{ $t("position_data.display_settings.position_data.upload") }}</v-btn
                >
              </v-row>
            </v-sheet>
          </v-col>
        </v-row>

        <ModalPluginRun
          v-if="showBytetrackModal"
          v-model="showBytetrackModal"
          plugin="bytetrack"
          :name="$t('modal.plugin.bytetrack.plugin_name')"
          :description="$t('modal.plugin.bytetrack.plugin_description')"
          :paramsFactory="bytetrackParams"
          :videoId="playerStore.videoId"
          runButtonDataTour="posdata-bytetrack-run"
        />
        <ModalPluginRun
          v-if="showDltModal"
          v-model="showDltModal"
          plugin="calibration_static_dlt"
          :name="$t('modal.plugin.calibration_static_dlt.plugin_name')"
          :description="$t('modal.plugin.calibration_static_dlt.plugin_description')"
          :paramsFactory="dltParams"
          :videoId="playerStore.videoId"
          runButtonDataTour="posdata-dlt-apply"
        />
      </template>

      <v-row style="justify-content: center" class="mt-12">
        <v-btn :disabled="!hasAvailablePositionData" @click="showModalPositionDataSelect = true">{{
          $t("position_data.display_settings.position_data.select")
        }}</v-btn>
        <ModalPositionDataSelect
          v-if="showModalPositionDataSelect"
          v-model="showModalPositionDataSelect"
        />
      </v-row>

      <ModalPositionDataUpload
        v-if="showModalPositionDataUpload"
        v-model="showModalPositionDataUpload"
      />
    </v-col>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import { usePluginRunStore } from "@/stores/plugin_run";
import { bytetrackParams, dltParams } from "@/composables/usePluginParams";
import ModalPluginRun from "@/components/app/app-bar/ModalPluginRun.vue";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";

const playerStore = usePlayerStore();
const userStore = useUserStore();
const pluginRunStore = usePluginRunStore();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const showModalPositionDataUpload = ref(false);
const showModalPositionDataSelect = ref(false);
const showBytetrackModal = ref(false);
const showDltModal = ref(false);

const hasAvailablePositionData = computed(() => {
  const runs = pluginRunStore.forVideo(playerStore.videoId);
  const isDone = (type) => runs.some((r) => r.type === type && r.status === "DONE");
  return (isDone("bytetrack") && isDone("calibration_static_dlt")) || isDone("posdata_convert");
});
</script>
