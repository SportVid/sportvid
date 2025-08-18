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

      <v-card-text class="pt-4">
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

          <v-file-input
            v-model="positionData.file"
            :rules="[validateFile]"
            :label="$t('modal.position_data.upload.file')"
            prepend-icon="mdi-file-upload"
            class="mt-2"
            show-size
            persistent-hint
          />

          <v-select
            v-model="positionData.format"
            :items="positionDataStore.provider"
            item-title="name"
            item-value="id"
            :label="$t('modal.position_data.upload.format')"
            variant="underlined"
            class="mt-2"
            prepend-icon="mdi-menu-swap"
          />

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
  file: null,
  format: null,
});

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

const disabled = computed(
  () =>
    !checkbox.value ||
    !positionData.value.title ||
    !positionData.value.file ||
    !positionData.value.file ||
    !fileValid.value
);

const uploadPositionData = async () => {
  const params = {
    title: positionData.value.title,
    file: positionData.value.file,
    format: positionData.value.format,
  };

  await positionDataStore.uploadPositionData(params);
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
</style>
