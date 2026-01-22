<template>
  <v-dialog v-model="dialog" width="700px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.position_data.upload.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="pt-4" style="overflow-y: auto">
        <v-form>
          <v-text-field
            v-model="positionData.title"
            :counter="120"
            persistent-counter
            variant="underlined"
            :label="$t('modal.position_data.upload.name')"
            required
            clearable
            clear-icon="mdi-close-circle-outline"
            prepend-icon="mdi-pencil"
          />

          <v-select
            v-model="positionData.format"
            :items="positionDataStore.provider"
            item-title="name"
            item-value="id"
            :label="$t('modal.position_data.upload.format')"
            variant="underlined"
            class="mt-2"
            prepend-icon="mdi-menu"
          />

          <v-file-input
            v-model="positionData.file"
            :rules="[validateFile]"
            :label="$t('modal.position_data.upload.file')"
            prepend-icon="mdi-file-upload"
            class="mt-2"
            show-size
            persistent-hint
          />

          <v-file-input
            v-if="positionData.format === 'dfl'"
            v-model="positionData.metaData"
            :rules="[validateFile]"
            :label="$t('modal.position_data.upload.meta_data')"
            prepend-icon="mdi-file-upload"
            class="mt-5"
            show-size
            persistent-hint
          />

          <v-select
            v-if="positionData.format === 'kinexon'"
            v-model="positionData.delimiter"
            :items="delimiters"
            item-title="title"
            item-value="value"
            :label="$t('modal.position_data.upload.delimiter')"
            variant="underlined"
            class="mt-4"
            prepend-icon="mdi-menu"
          />

          <v-select
            v-if="positionData.format === 'kinexon'"
            v-model="positionData.origin"
            :items="origins"
            item-title="title"
            item-value="value"
            :label="$t('modal.position_data.upload.origin')"
            variant="underlined"
            class="mt-4"
            prepend-icon="mdi-menu"
          />

          <v-text-field
            v-if="positionData.format === 'kinexon'"
            v-model="positionData.teamIdBall"
            variant="underlined"
            :label="$t('modal.position_data.upload.team_id_ball')"
            clearable
            clear-icon="mdi-close-circle-outline"
            prepend-icon="mdi-pencil"
            class="mt-4"
          />

          <v-text-field
            v-model="positionData.fps"
            type="number"
            min="1"
            variant="underlined"
            class="mt-2"
            :label="$t('modal.position_data.upload.fps.title')"
            prepend-icon="mdi-numeric"
          >
            <template #append-inner>
              <v-tooltip class="fps-tooltip" :text="$t('modal.position_data.upload.fps.tooltip')">
                <template #activator="{ props }">
                  <v-icon v-bind="props" color="primary">mdi-information-outline</v-icon>
                </template>
              </v-tooltip>
            </template>
          </v-text-field>

          <v-progress-linear
            v-if="isUploading"
            v-model="uploadingProgress"
            class="mt-1 ml-10 mb-n2"
            style="max-width: calc(100% - 40px)"
          />

          <v-checkbox v-model="checkbox" required class="ml-n2">
            <template #label>
              <i18n-t keypath="terms_of_service.confirmation" tag="span">
                <template #title>
                  <router-link
                    to="/terms-of-service"
                    target="_blank"
                    class="text-primary terms-of-service-link"
                  >
                    {{ $t("terms_of_service.title") }}
                  </router-link>
                </template>
              </i18n-t>
            </template>
          </v-checkbox>

          <v-btn class="mr-4 mt-n4" :disabled="disabled" @click="uploadPositionData">
            {{ $t("button.upload") }}
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { usePositionDataStore } from "@/stores/position_data";

const positionDataStore = usePositionDataStore();
const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const positionData = ref({
  title: null,
  format: null,
  file: null,
  metaData: null,
  delimiter: null,
  origin: null,
  teamIdBall: null,
  fps: null,
});
const delimiters = [
  { value: ",", title: t("modal.position_data.upload.delimiters.comma") },
  { value: ";", title: t("modal.position_data.upload.delimiters.semicolon") },
  { value: "\t", title: t("modal.position_data.upload.delimiters.tab") },
  { value: " ", title: t("modal.position_data.upload.delimiters.space") },
  { value: "|", title: t("modal.position_data.upload.delimiters.pipe") },
];
const origins = [
  { value: "kickoff", title: t("modal.position_data.upload.origins.kickoff") },
  { value: "bottom-left", title: t("modal.position_data.upload.origins.bottom_left") },
];

const checkbox = ref(false);
const fileValid = ref(false);
const validateFile = (file) => {
  if (Array.isArray(file)) {
    file = file[0];
  }

  if (!file || !file.name) {
    fileValid.value = false;
    return t("modal.position_data.upload.validate.file_required");
  }
  if (!(file.name.endsWith(".csv") || file.name.endsWith(".xml"))) {
    fileValid.value = false;
    return t("modal.position_data.upload.validate.file_format_invalid");
  }

  fileValid.value = true;
  return true;
};

const isUploading = computed(() => positionDataStore.isUploading);
const uploadingProgress = computed(() => positionDataStore.progress);

const disabled = computed(() => {
  if (
    !checkbox.value ||
    !positionData.value.title ||
    !positionData.value.format ||
    !positionData.value.file ||
    !fileValid.value
  ) {
    return true;
  }
  if (positionData.value.format === "dfl" && !positionData.value.metaData) {
    return true;
  }
  if (
    positionData.value.format === "kinexon" &&
    !positionData.value.delimiter &&
    !positionData.value.origin
  ) {
    return true;
  }

  return false;
});

const uploadPositionData = async () => {
  await positionDataStore.uploadPositionData(positionData.value);
  dialog.value = false;
  fileValid.value = false;
};

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
</script>

<style scoped>
.terms-of-service-link {
  font-weight: bold;
  text-decoration: none;
}

.terms-of-service-link:hover {
  text-decoration: underline;
}

.fps-tooltip ::v-deep(.v-overlay__content) {
  background-color: rgb(var(--v-theme-primary));
}
</style>
