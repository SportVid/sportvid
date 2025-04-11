<template>
  <v-dialog v-model="show" max-width="1000">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" text block large>
        <v-icon left>{{ "mdi-plus-thick" }}</v-icon>
        {{ $t("modal.timeline.create.title") }}
      </v-btn>
    </template>
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.timeline.create.title") }}

        <v-btn icon @click="() => (show.value = false)" absolute top right>
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-text-field
          :label="$t('modal.timeline.create.name')"
          prepend-icon="mdi-pencil"
          v-model="name"
        ></v-text-field>
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn class="mr-4" @click="submit" :disabled="isSubmitting.value || !name">
          {{ $t("modal.timeline.create.submit") }}
        </v-btn>
        <v-btn @click="() => (show.value = false)">
          {{ $t("modal.timeline.create.close") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, watch } from "vue";
import { useTimelineStore } from "@/stores/timeline";

export default {
  props: {
    timeline: {
      type: Object,
      required: false,
    },
  },
  setup(props, { emit }) {
    const show = ref(false);
    const isSubmitting = ref(false);
    const name = ref(null);
    const timelineStore = useTimelineStore();

    const submit = async () => {
      if (isSubmitting.value) return;
      isSubmitting.value = true;

      try {
        await timelineStore.create({ name: name.value });
        show.value = false;
      } finally {
        isSubmitting.value = false;
      }
    };

    watch(show, (value) => {
      if (value) {
        name.value = null;
        emit("close");
      }
    });

    return {
      show,
      isSubmitting,
      name,
      submit,
      $t: (key) => key, // Mock translation function if needed
    };
  },
};
</script>
