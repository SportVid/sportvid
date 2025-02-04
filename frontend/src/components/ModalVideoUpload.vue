<template>
  <v-card 
    :class="['d-flex', 'flex-column', 'ma-6']" 
    style="text-align: center;" 
    flat 
    color="transparent" 
    width="210"
  >
    <v-dialog v-model="dialog" max-width="1000">
      <template v-slot:activator="{ props }">
        <v-btn :disabled="!canUpload" color="primary" v-bind="props">
          {{ $t("modal.video.upload.link") }}
          <v-icon class="ms-2">{{ "mdi-plus-circle" }}</v-icon>
        </v-btn>
      </template>

      <v-card>
        <v-toolbar color="primary" dark class="pl-4">
          {{ $t("modal.video.upload.title") }}
        </v-toolbar>

        <v-card-text class="pt-4">
          <v-form>
            <v-text-field
              v-model="video.title" 
              :counter="120"
              persistent-counter 
              variant="underlined" 
              :label="$t('modal.video.upload.name')"
              required></v-text-field>
            <v-file-input
              v-model="video.file"
              :rules="[validateFile]"
              :label="$t('modal.video.upload.input')"
              filled
              prepend-icon="mdi-movie-filter"
              class="mt-2"
            ></v-file-input>

            <v-checkbox
              v-model="checkbox" 
              label="Do you agree with the terms of services?" 
              required 
              class="mt-0">
            </v-checkbox>

            <v-progress-linear
              v-if="isUploading"
              v-model="uploadingProgress"
              class="mb-4 mt-n4"></v-progress-linear>

            <v-btn class="mr-4" :disabled="disabled" @click="uploadVideo">
              {{ $t("modal.video.upload.update") }}
            </v-btn>
            <v-btn @click="dialog = false">
              {{ $t("modal.video.upload.close") }}
            </v-btn>
          </v-form>
        </v-card-text>
      </v-card>
    </v-dialog>
    <span v-if="!canUpload" class="text-error">
      You have uploaded the maximum amount of videos that you are allowed to. If
      you require more, please contact abc@xyz.de.
    </span>
    <span v-if="canUpload">
      Videos uploaded: {{ numVideos }} out of {{ allowance }}
    </span>
    <span v-if="canUpload">
      Max. file size: {{ maxSizeInWords }}
    </span>
  </v-card>
</template>

<script>
import { ref, computed } from "vue";
import { useVideoUploadStore } from "@/stores/video_upload";
import { useUserStore } from "@/stores/user";
import { useVideoStore } from "@/stores/video";

export default {
  setup() {
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
    const disabled = computed(() => !checkbox.value || !fileValid.value || uploadingProgress.value !== 0);
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
        return "Please select a file.";
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

    return {
      video,
      analysers,
      selectedAnalysers,
      checkbox,
      dialog,
      fileValid,
      canUpload,
      disabled,
      isUploading,
      uploadingProgress,
      allowance,
      numVideos,
      maxSizeInWords,
      maxSize,
      validateFile,
      uploadVideo,
    };
  },
};
</script>
