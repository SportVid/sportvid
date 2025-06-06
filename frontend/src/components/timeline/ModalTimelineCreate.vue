<template>
  <v-dialog v-model="dialog" width="800px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.timeline.create.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="d-flex align-center">
        <v-text-field
          v-model="name"
          :label="$t('modal.timeline.create.name')"
          prepend-icon="mdi-pencil"
          variant="underlined"
          class="mr-6"
        />

        <v-btn @click="submit" :disabled="isSubmitting || !name">
          {{ $t("modal.timeline.create.submit") }}
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
    type: Object,
    required: false,
  },
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits();

const dialog = ref(props.modelValue);
const isSubmitting = ref(false);
const name = ref(null);
const timelineStore = useTimelineStore();

const submit = async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;

  await timelineStore.create({ name: name.value });

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
