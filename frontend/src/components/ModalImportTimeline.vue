<template>
  <v-dialog v-model="show" max-width="1000">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" text block large>
        <v-icon left>{{ "mdi-import" }}</v-icon>
        {{ $t("modal.timeline.import.title") }}
      </v-btn>
    </template>
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.timeline.import.title") }}

        <v-btn icon @click="() => (show.value = false)" absolute top right>
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-file-input
          v-model="importfile.value"
          label="Select an ELAN file to import [eaf]"
          filled
          prepend-icon="mdi-file"
        ></v-file-input>
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn class="mr-4" @click="submit" :disabled="isSubmitting.value">
          {{ $t("modal.timeline.import.update") }}
        </v-btn>
        <v-btn @click="() => (show.value = false)">{{
          $t("modal.timeline.import.close")
        }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, watch } from "vue";
import { useTimelineStore } from "@/stores/timeline";

export default {
  setup(_, { emit }) {
    const show = ref(false);
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
      show.value = false;
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
      importfile,
      submit
    };
  },
};
</script>
