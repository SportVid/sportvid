<template>
  <v-dialog v-model="show" max-width="1000">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" text block large>
        <v-icon left>{{ "mdi-trash-can-outline" }}</v-icon>
        {{ $t("modal.timeline.delete.link") }}
      </v-btn>
    </template>
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.timeline.delete.title") }}
        <v-btn icon @click="show = false" absolute top right>
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text> {{ $t("modal.timeline.delete.question") }}</v-card-text>
      <v-card-actions class="pt-0">
        <v-btn class="mr-4" @click="submit" :disabled="isSubmitting">
          {{ $t("modal.timeline.delete.yes") }}
        </v-btn>
        <v-btn @click="show = false">{{
          $t("modal.timeline.delete.no")
        }}</v-btn>
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
      required: true,
    },
  },
  setup(props, { emit }) {
    const timelineStore = useTimelineStore(); 
    const show = ref(false);
    const isSubmitting = ref(false);

    const submit = async () => {
      if (isSubmitting.value) {
        return;
      }
      isSubmitting.value = true;

      await timelineStore.delete(props.timeline);

      isSubmitting.value = false;
      show.value = false;
    };

    watch(show, (value) => {
      if (value) {
        emit("close");
      }
    });

    return {
      show,
      isSubmitting,
      submit,
    };
  },
};
</script>
