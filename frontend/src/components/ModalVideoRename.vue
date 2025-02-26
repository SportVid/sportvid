<template>
  <v-dialog v-model="show" max-width="800">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" variant="outlined" class="ml-n2">
        <v-icon class="mr-1">{{ "mdi-pencil" }}</v-icon>
        {{ $t("video_view.rename") }}
      </v-btn>
    </template>

    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.video.rename.title") }}

        <v-spacer />

        <v-btn icon @click="show = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pt-4 d-flex align-center">
        <v-text-field
          v-model="name"
          :label="$t('modal.video.rename.name')"
          prepend-icon="mdi-pencil"
          variant="underlined"
          class="mr-6"
        />

        <v-btn class="" @click="submit" :disabled="isSubmitting || !name">
          {{ $t("modal.video.rename.update") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from "vue";
import { useVideoStore } from "@/stores/video";

export default {
  props: {
    video: {
      type: [String, Number],
      required: true,
    },
  },
  setup(props, { emit }) {
    const videoStore = useVideoStore();
    const show = ref(false);
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
      if (isSubmitting.value) {
        return;
      }
      isSubmitting.value = true;

      await videoStore.rename({
        videoId: props.video,
        name: name.value,
      });

      isSubmitting.value = false;
      show.value = false;
    };

    watch(show, (value) => {
      if (value) {
        nameProxy.value = null;
        emit("close");
      }
    });

    return {
      show,
      isSubmitting,
      name,
      submit,
    };
  },
};
</script>
