<template>
  <v-dialog v-model="dialog" width="500px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.event_data.upload.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="pt-4" style="overflow-y: auto" data-tour="eventdata-manual-upload-modal">
        <v-form v-if="canUpload">
          <v-text-field
            v-model="eventData.title"
            :counter="120"
            persistent-counter
            variant="underlined"
            :label="$t('modal.event_data.upload.name')"
            required
            clearable
            clear-icon="mdi-close-circle-outline"
            prepend-icon="mdi-pencil"
          />

          <v-select
            v-model="eventData.format"
            :items="eventDataProviders"
            item-title="name"
            item-value="id"
            :label="$t('modal.event_data.upload.format')"
            variant="underlined"
            class="mt-2"
            prepend-icon="mdi-menu"
          />

          <v-file-input
            v-model="eventData.file"
            :rules="[validateFile]"
            :label="$t('modal.event_data.upload.file')"
            prepend-icon="mdi-file-upload"
            class="mt-2"
            density="comfortable"
            show-size
            :hint="
              $t('modal.event_data.upload.hint', { maxSize: sizeInWords(userStore.maxFileSize) })
            "
            persistent-hint
            variant="underlined"
          />

          <div v-if="isUploading" class="d-flex align-center mt-3" style="gap: 10px">
            <v-progress-linear v-model="uploadingProgress" class="flex-grow-1" />
            <span
              v-if="uploadEtaText"
              class="text-caption text-medium-emphasis text-no-wrap"
            >
              {{ uploadEtaText }}
            </span>
          </div>

          <v-checkbox v-model="checkbox" required class="ml-n2 mt-4">
            <template #label>
              <i18n-t keypath="terms_of_use.confirmation" tag="span">
                <template #title>
                  <router-link
                    to="/terms-of-use"
                    target="_blank"
                    class="text-primary terms-of-use-link"
                  >
                    {{ $t("terms_of_use.title") }}
                  </router-link>
                </template>
              </i18n-t>
            </template>
          </v-checkbox>

          <v-btn
            class="mr-4 mt-n4"
            :disabled="disabled"
            @click="uploadEventData"
            data-tour="eventdata-manual-upload"
          >
            {{ $t("button.upload") }}
          </v-btn>
        </v-form>

        <div v-else class="text-center my-4">
          <span class="text-error">
            {{ $t("modal.event_data.upload.upload_denied") }}
          </span>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { getEtaDisplay } from "@/plugins/time";
import { useEventsStore } from "@/stores/events";
import { useUserStore } from "@/stores/user";

const eventsStore = useEventsStore();
const userStore = useUserStore();

const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

// No real event-detection backend exists yet (see events.js) -- these are purely cosmetic
// choices for the dummy upload, not real parser identifiers the way positionDataStore.provider's
// are (position data actually gets parsed server-side against one of those).
const eventDataProviders = [
  { id: "action_spotting_csv", name: "Action Spotting (CSV)" },
  { id: "manual_csv", name: t("modal.event_data.upload.provider_manual") },
];

const eventData = ref({
  title: null,
  format: null,
  file: null,
});

const checkbox = ref(false);
const fileValid = ref(false);

const sizeInWords = (size) => {
  if (size === null || size === undefined) return "0 B";

  const units = ["B", "kB", "MB", "GB", "TB"];
  let i = 0;
  let s = size;

  while (s >= 1024 && i < units.length - 1) {
    s = s / 1024;
    i++;
  }

  return Math.round(s * 100) / 100 + units[i];
};

const validateFile = (file) => {
  if (Array.isArray(file)) {
    file = file[0];
  }

  if (!file || !file.name) {
    fileValid.value = false;
    return t("modal.event_data.upload.validate.file_required", {
      maxSize: sizeInWords(userStore.maxFileSize),
    });
  }
  if (file.size > userStore.maxFileSize) {
    fileValid.value = false;
    return t("modal.event_data.upload.validate.file_exceeds", {
      maxSize: sizeInWords(userStore.maxFileSize),
    });
  }

  fileValid.value = true;
  return true;
};

// Wired to the events store's upload tracker -- inert until a real /event_data/upload
// endpoint feeds it (see events.js), then the bar + ETA light up like the other modals.
const isUploading = computed(() => eventsStore.isUploadingEventData);
const uploadingProgress = computed(() => eventsStore.eventUploadProgress);
const uploadEtaText = computed(() => {
  const display = getEtaDisplay(eventsStore.eventUploadEtaSeconds);
  return display ? t("progress.eta", { time: display }) : "";
});

const canUpload = computed(() => userStore.remainingStorageSize > 0);
const disabled = computed(() => {
  return (
    !checkbox.value || !eventData.value.title || !eventData.value.format || !fileValid.value
  );
});

// No backend endpoint exists yet -- adds a client-side-only entry to eventsStore's list (see
// uploadEventDataSet) instead of an actual API upload, same "dummy for now" approach events.js
// already takes for eventsData itself. Doesn't auto-select the new entry -- picking it is still
// a separate step via ModalEventDataSelect (mirrors ModalPositionDataUpload.vue, which likewise
// only refreshes positionDataStore's list rather than loading the upload straight away).
const uploadEventData = () => {
  eventsStore.uploadEventDataSet({
    title: eventData.value.title,
    format: eventData.value.format,
  });
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
.terms-of-use-link {
  font-weight: bold;
  text-decoration: none;
}

.terms-of-use-link:hover {
  text-decoration: underline;
}
</style>
