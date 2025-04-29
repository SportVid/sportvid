<template>
  <v-dialog v-model="dialog" width="800">
    <template #activator="{ props }">
      <v-btn size="small" v-bind="props" variant="outlined">
        <v-icon class="mr-1">{{ "mdi-pencil" }}</v-icon>
        {{ $t("button.rename") }}
      </v-btn>
    </template>

    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.video.rename.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="pt-4 d-flex align-center">
        <v-text-field
          v-model="name"
          :label="$t('modal.video.rename.video_title')"
          prepend-icon="mdi-pencil"
          variant="underlined"
          class="mr-6"
        />

        <v-btn @click="submit" :disabled="isSubmitting || !name">
          {{ $t("button.rename") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useVideoStore } from "@/stores/video";

const props = defineProps({
  video: {
    type: [String, Number],
    required: true,
  },
});

const emit = defineEmits();

const videoStore = useVideoStore();

const dialog = ref(false);
const isSubmitting = ref(false);
const nameProxy = ref(null);

const name = computed({
  get() {
    const videoData = videoStore.get(props.video);
    const name = videoData ? videoData.name : "";
    return nameProxy.value === null ? name : nameProxy.value;
  },
  set(val) {
    nameProxy.value = val;
  },
});

const submit = async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;

  await videoStore.rename({
    videoId: props.video,
    name: name.value,
  });

  isSubmitting.value = false;
  dialog.value = false;
};

watch(dialog, (value) => {
  if (value) {
    nameProxy.value = null;
    emit("close");
  }
});
</script>
