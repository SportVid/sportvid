<template>
  <v-dialog v-model="dialog" max-width="550">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.timeline.delete.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="d-flex align-center justify-center">
        {{ $t("modal.timeline.delete.question") }}
        <v-btn class="ml-6" @click="submit" :disabled="isSubmitting">
          {{ $t("button.delete") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { useTimelineStore } from "@/stores/timeline";

const props = defineProps({
  timeline: {
    type: String,
    required: true,

    modelValue: {
      type: Boolean,
      default: false,
    },
  },
});

const emit = defineEmits();

const timelineStore = useTimelineStore();
const dialog = ref(props.modelValue);
const isSubmitting = ref(false);

const submit = async () => {
  if (isSubmitting.value) {
    return;
  }
  isSubmitting.value = true;

  await timelineStore.deleteTimeline(props.timeline);

  isSubmitting.value = false;
  dialog.value = false;
};

watch(dialog, (value) => {
  if (value) {
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
