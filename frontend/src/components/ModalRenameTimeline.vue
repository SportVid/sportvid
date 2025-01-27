<template>
  <v-dialog v-model="show" max-width="1000">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" text block large>
        <v-icon left>{{ "mdi-pencil" }}</v-icon>
        {{ $t("modal.timeline.rename.link") }}
      </v-btn>
    </template>
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.timeline.rename.title") }}
        
        <v-btn icon @click="closeDialog" absolute top right>
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-text-field
          :label="$t('modal.timeline.rename.name')"
          prepend-icon="mdi-pencil"
          v-model="name"
        ></v-text-field>
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn class="mr-4" @click="submit" :disabled="isSubmitting || !name">
          {{ $t("modal.timeline.rename.update") }}
        </v-btn>
        <v-btn @click="closeDialog">{{ $t("modal.timeline.rename.close") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from "vue";
import { useTimelineStore } from "@/stores/timeline";

export default {
  props: ["timeline"],
  
  setup(props) {
    const show = ref(false);
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
      }
    });

    const submit = async () => {
      if (isSubmitting.value) return;
      isSubmitting.value = true;

      await timelineStore.rename({
        timelineId: props.timeline,
        name: name.value,
      });

      isSubmitting.value = false;
      show.value = false;
    };

    watch(show, (value) => {
      if (value) {
        nameProxy.value = null;
        emitClose();
      }
    });

    const closeDialog = () => {
      show.value = false;
    };

    const emitClose = () => {
      props.$emit("close");
    };

    return {
      show,
      isSubmitting,
      name,
      submit,
      closeDialog,
    };
  }
};
</script>
