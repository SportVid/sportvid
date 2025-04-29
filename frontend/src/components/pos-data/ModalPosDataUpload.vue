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
            v-model="posData.title"
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
            v-model="posData.file"
            :label="$t('modal.position_data.upload.file')"
            prepend-icon="mdi-file-upload"
            class="mt-2"
            show-size
            persistent-hint
          />

          <v-progress-linear
            v-if="isUploading"
            v-model="uploadingProgress"
            class="mt-1 ml-10 mb-n2"
            style="max-width: calc(100% - 40px)"
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

          <v-btn class="mr-4 mt-n4" :disabled="disabled" @click="uploadPosData">
            {{ $t("button.upload") }}
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useBboxesStore } from "@/stores/bboxes";

const bboxesStore = useBboxesStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const posData = ref({
  title: "",
  file: null,
});

const checkbox = ref(false);

const isUploading = ref(0);
const uploadingProgress = ref(0);

const disabled = computed(() => !checkbox.value || !posData.value.title || !posData.value.file);

const uploadPosData = async () => {
  const file = posData.value.file;
  const reader = new FileReader();
  reader.readAsText(file, "UTF-8");
  reader.onload = function () {
    const csvText = reader.result;
    const newUpload = {
      id: Date.now(),
      title: posData.value.title,
      file: csvText,
    };
    const existing = JSON.parse(localStorage.getItem("uploadedPosDataList") || "[]");
    existing.push(newUpload);
    localStorage.setItem("uploadedPosDataList", JSON.stringify(existing));
    bboxesStore.posDataUploadSuccess = true;
    dialog.value = false;
  };
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
