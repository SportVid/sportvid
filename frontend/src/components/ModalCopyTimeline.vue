<template>
  <v-dialog v-model="show" max-width="1000">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" text block large>
        <v-icon left>{{ "mdi-content-copy" }}</v-icon>
        {{ $t("modal.timeline.duplicate.link") }}
      </v-btn>
    </template>
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.timeline.duplicate.title") }}

        <v-btn icon @click="() => (show = false)" absolute top right>
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-text-field
          :label="$t('modal.timeline.duplicate.name')"
          prepend-icon="mdi-pencil"
          v-model="name"
        ></v-text-field>

        <v-checkbox
          v-model="includeannotations"
          :label="$t('modal.timeline.duplicate.includeannotations')"
        ></v-checkbox>
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn class="mr-4" @click="submit" :disabled="isSubmitting">
          {{ $t("modal.timeline.duplicate.update") }}
        </v-btn>
        <v-btn @click="() => (show = false)">
          {{ $t("modal.timeline.duplicate.close") }}
        </v-btn>
      </v-card-actions>
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
});

const timelineStore = useTimelineStore();

const show = ref(false);
const isSubmitting = ref(false);
const nameProxy = ref(null);
const includeannotations = ref(true);

const name = computed({
  get() {
    const timelineName = timelineStore.get(props.timeline).name + " (1)";
    return nameProxy.value === null ? timelineName : nameProxy.value;
  },
  set(val) {
    nameProxy.value = val;
  },
});

const submit = async () => {
  if (isSubmitting.value) return;

  isSubmitting.value = true;

  await timelineStore.duplicate({
    id: props.timeline,
    name: name.value,
    includeannotations: includeannotations.value,
  });

  isSubmitting.value = false;
  show.value = false;
};

watch(show, (value) => {
  if (value) {
    nameProxy.value = null;
  }
});
</script>
