<template>
  <v-card
    :class="['d-flex', 'flex-column']"
    style="text-align: center"
    flat
    color="transparent"
    width="210"
  >
    <v-dialog v-model="dialog" max-width="1000">
      <template v-slot:activator="{ props }">
        <v-btn :disabled="!canUpload" :color="!canUpload ? 'light-grey' : 'primary'" v-bind="props">
          {{ $t("modal.video.upload.link") }}
          <v-icon class="ms-2">mdi-plus-circle</v-icon>
        </v-btn>
      </template>

      <v-card>
        <v-toolbar color="primary" dark class="pl-4 pr-1 text-h6">
          {{ $t("modal.video.upload.title") }}

          <v-spacer />

          <v-btn icon @click="dialog = false" variant="plain" color="grey">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <v-card-text class="pt-4">
          <v-form>
            <v-text-field
              v-model="video.title"
              :counter="120"
              persistent-counter
              variant="underlined"
              :label="$t('modal.video.upload.name')"
              required
              clearable
              clear-icon="mdi-close-circle-outline"
              prepend-icon="mdi-pencil"
            />

            <v-file-input
              v-model="video.file"
              :rules="[validateFile]"
              :label="$t('modal.video.upload.input')"
              filled
              prepend-icon="mdi-movie-filter"
              class="mt-2"
              show-size
              :hint="`Maximum file size: ${maxSizeInWords}`"
              persistent-hint
            />

            <v-progress-linear
              v-if="isUploading"
              v-model="uploadingProgress"
              class="mt-n2 ml-10 mb-4"
              style="max-width: calc(100% - 40px)"
            />

            <v-checkbox v-model="checkbox" required class="ml-n2">
              <template v-slot:label>
                <span class="ml-2">Do you agree with the terms of services?</span>
              </template>
            </v-checkbox>

            <v-btn class="mr-4 mt-n4" :disabled="disabled" @click="uploadVideo">
              {{ $t("modal.video.upload.update") }}
            </v-btn>
          </v-form>
        </v-card-text>
      </v-card>
    </v-dialog>
    <span v-if="!canUpload" class="text-error">
      You have uploaded the maximum amount of videos that you are allowed to. If you require more,
      please contact abc@xyz.de.
    </span>
    <span v-if="canUpload"> Videos uploaded: {{ numVideos }} out of {{ allowance }} </span>
  </v-card>
</template>

<script setup>
import { ref, computed } from "vue";
import { useVideoUploadStore } from "@/stores/video_upload";
import { useUserStore } from "@/stores/user";
import { useVideoStore } from "@/stores/video";

const videoUploadStore = useVideoUploadStore();
const userStore = useUserStore();
const videoStore = useVideoStore();

const video = ref({
  title: "",
  file: null,
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

const canUpload = computed(() => userStore.allowance > videoStore.all.length);
const disabled = computed(
  () => !checkbox.value || !fileValid.value || uploadingProgress.value !== 0
);
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
    return "Please select a file with a maximum file size of " + maxSizeInWords.value;
  }
  if (file.size > maxSize.value) {
    fileValid.value = false;
    return "File exceeds your maximum file size of " + maxSizeInWords.value;
  }
  if (!file.name.endsWith(".mp4")) {
    fileValid.value = false;
    return "File is not in the .mp4 format.";
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
