<template>
  <v-card
    :class="['d-flex', 'flex-column']"
    style="text-align: center"
    flat
    color="transparent"
    width="210"
  >
    <v-dialog v-model="dialog" width="700">
      <template #activator="{ props }">
        <v-btn :disabled="!canUpload" :color="!canUpload ? 'light-grey' : 'primary'" v-bind="props">
          {{ $t("button.upload_video") }}
          <v-icon class="ms-2">mdi-plus-circle</v-icon>
        </v-btn>
      </template>

      <v-card>
        <v-toolbar color="primary">
          <v-toolbar-title class="text-h6">
            {{ $t("modal.video.upload.title") }}
          </v-toolbar-title>

          <template #append>
            <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
          </template>
        </v-toolbar>

        <v-card-text class="pt-4">
          <v-form>
            <v-text-field
              v-model="video.title"
              :counter="120"
              persistent-counter
              variant="underlined"
              :label="$t('modal.video.upload.video_title')"
              required
              clearable
              clear-icon="mdi-close-circle-outline"
              prepend-icon="mdi-pencil"
            />

            <v-file-input
              v-model="video.file"
              :rules="[validateFile]"
              :label="$t('modal.video.upload.file')"
              prepend-icon="mdi-movie-filter"
              class="mt-2"
              density="comfortable"
              show-size
              :hint="$t('modal.video.upload.hint', { maxSize: maxSizeInWords })"
              persistent-hint
            />

            <v-divider class="my-4 mx-16" />

            <v-select
              v-model="video.division"
              :items="divisions"
              :label="$t('modal.video.upload.division')"
              density="compact"
              variant="outlined"
            />

            <v-row dense>
              <v-col cols="5">
                <v-select
                  v-model="video.currentPosition"
                  :items="positions"
                  :label="$t('modal.video.upload.position')"
                  density="compact"
                  variant="outlined"
                />
              </v-col>
              <v-col cols="2" class="d-flex justify-center mt-2">
                <span>out of</span>
              </v-col>
              <v-col cols="5">
                <v-select
                  v-model="video.totalNumberofTeams"
                  :items="positions"
                  :label="$t('modal.video.upload.total_teams')"
                  density="compact"
                  variant="outlined"
                />
              </v-col>
            </v-row>

            <v-select
              v-model="video.ageGroup"
              :items="ageGroups"
              :label="$t('modal.video.upload.age_group')"
              density="compact"
              variant="outlined"
            />

            <v-divider class="mb-6 mx-16" />

            <v-progress-linear
              v-if="isUploading"
              v-model="uploadingProgress"
              class="mt-n1 ml-16"
              style="max-width: calc(100% - 128px)"
            />

            <v-checkbox v-model="checkbox" required class="ml-n2">
              <template #label>
                <span class="ml-2">
                  Do you agree with the
                  <router-link
                    to="/terms-of-service"
                    target="_blank"
                    class="text-primary terms-of-service-link"
                  >
                    Terms of Service</router-link
                  >?
                </span>
              </template>
            </v-checkbox>

            <v-btn class="mr-4 mt-n4" :disabled="disabled" @click="uploadVideo">
              {{ $t("button.upload") }}
            </v-btn>
          </v-form>
        </v-card-text>
      </v-card>
    </v-dialog>
    <span v-if="!canUpload" class="text-error">
      {{ $t("modal.video.upload.upload_denied") }}
    </span>
    <span v-if="canUpload">
      {{ $t("modal.video.upload.videos_uploaded", { numVideos: numVideos, allowance: allowance }) }}
    </span>
  </v-card>
</template>

<script setup>
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useVideoUploadStore } from "@/stores/video_upload";
import { useUserStore } from "@/stores/user";
import { useVideoStore } from "@/stores/video";

const { t } = useI18n();

const videoUploadStore = useVideoUploadStore();
const userStore = useUserStore();
const videoStore = useVideoStore();

const video = ref({
  title: null,
  file: null,
  division: null,
  currentPosition: null,
  totalNumberofTeams: null,
  ageGroup: null,
});
const analysers = ref([
  {
    label: "Shot Detection",
    disabled: false,
    model: "shotdetection",
  },
]);
const selectedAnalysers = ref(["shotdetection"]);
const checkbox = ref(false);
const dialog = ref(false);
const fileValid = ref(false);

const divisions = ref([
  "1. Bundesliga",
  "2. Bundesliga",
  "3. Liga",
  "Regionalliga",
  "Oberliga",
  "Landesliga",
  "Bezirksliga",
  "Kreisliga",
]);
const positions = ref(Array.from({ length: 20 }, (_, i) => String(i + 1)));
const ageGroups = ref([
  "Herren",
  "U19 Junioren",
  "U17 Junioren",
  "Damen",
  "U19 Juniorinnen",
  "U17 Juniorinnen",
]);

const canUpload = computed(() => userStore.allowance > videoStore.all.length);
const disabled = computed(() => {
  const v = video.value;
  return (
    !checkbox.value ||
    !fileValid.value ||
    uploadingProgress.value !== 0 ||
    !v.title ||
    !v.file ||
    !v.division ||
    !v.currentPosition ||
    !v.totalNumberofTeams ||
    !v.ageGroup
  );
});
const isUploading = computed(() => videoUploadStore.isUploading);
const uploadingProgress = computed(() => videoUploadStore.progress);
const allowance = computed(() => userStore.allowance);
const numVideos = computed(() => videoStore.all.length);

const maxSizeInWords = computed(() => {
  let size = userStore.maxVideoSize;
  let extensionId = 0;
  const extensions = [" B", " kB", " MB", " GB"];
  while (size > 1024) {
    size = (size / 1024).toFixed(2);
    extensionId++;
  }
  return size + extensions[extensionId];
});

const maxSize = computed(() => userStore.maxVideoSize);

const validateFile = (file) => {
  if (Array.isArray(file)) {
    file = file[0];
  }

  if (!file || !file.name) {
    fileValid.value = false;
    return t("modal.video.upload.validate.file_required", { maxSize: maxSizeInWords.value });
  }
  if (file.size > maxSize.value) {
    fileValid.value = false;
    return t("modal.video.upload.validate.file_exceeds", { maxSize: maxSizeInWords.value });
  }
  if (!file.name.endsWith(".mp4")) {
    fileValid.value = false;
    return t("modal.video.upload.validate.file_format_invalid");
  }

  fileValid.value = true;
  return true;
};

const uploadVideo = async () => {
  const params = {
    video: video.value,
    analyser: selectedAnalysers.value,
  };

  await videoUploadStore.upload(params);
  dialog.value = false;
  fileValid.value = false;
};
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
