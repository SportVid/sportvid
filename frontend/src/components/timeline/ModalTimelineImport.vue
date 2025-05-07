<template>
  <v-dialog v-model="dialog" max-width="800">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.timeline.import.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="d-flex align-center mt-6">
        <v-file-input
          v-model="importfile"
          :label="$t('modal.timeline.import.file')"
          filled
          prepend-icon="mdi-file"
          class="mr-6"
        />

        <v-btn class="mr-4 mt-n4" @click="submit" :disabled="isSubmitting">
          {{ $t("button.import") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { useTimelineStore } from "@/stores/timeline";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits();

const dialog = ref(props.modelValue);
const isSubmitting = ref(false);
const importfile = ref(null);
const name = ref(null);

const timelineStore = useTimelineStore();

const submit = async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;

  await timelineStore.importEAF({
    importfile: importfile.value,
  });

  isSubmitting.value = false;
  dialog.value = false;
};

watch(dialog, (value) => {
  if (value) {
    name.value = null;
    emit("close");
  }
});

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
