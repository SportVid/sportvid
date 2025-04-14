<template>
  <v-dialog v-model="dialog" width="600">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.timeline.rename.title") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pt-4 d-flex align-center">
        <v-text-field
          :label="$t('modal.timeline.rename.name')"
          prepend-icon="mdi-pencil"
          v-model="name"
          variant="underlined"
          class="mr-6"
        />
        <v-btn @click="submit" :disabled="isSubmitting || !name">
          {{ $t("modal.timeline.rename.update") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useTimelineStore } from "@/stores/timeline";

const props = defineProps({
  timeline: {
    type: String,
    required: true,
  },

  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits();

const dialog = ref(props.modelValue);
const isSubmitting = ref(false);
const nameProxy = ref(null);

const timelineStore = useTimelineStore();

const name = computed({
  get() {
    const name = timelineStore.get(props.timeline).name;
    return nameProxy.value === null ? name : nameProxy.value;
  },
  set(value) {
    nameProxy.value = value;
  },
});

const submit = async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;

  await timelineStore.rename({
    timelineId: props.timeline,
    name: name.value,
  });

  isSubmitting.value = false;
  dialog.value = false;
};

watch(dialog, (value) => {
  if (value) {
    nameProxy.value = null;
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
