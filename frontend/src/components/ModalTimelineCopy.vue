<template>
  <v-dialog v-model="dialog" max-width="600">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.timeline.duplicate.title") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text>
        <v-col>
          <v-row>
            <v-text-field
              :label="$t('modal.timeline.duplicate.name')"
              prepend-icon="mdi-pencil"
              v-model="name"
              variant="underlined"
              class="mr-6 mt-1"
            />
          </v-row>

          <v-row>
            <v-checkbox v-model="includeannotations" class="ml-n2 mt-n4">
              <template v-slot:label>
                <span class="ml-2">{{ $t("modal.timeline.duplicate.includeannotations") }}</span>
              </template>
            </v-checkbox>
          </v-row>
          <v-row>
            <v-btn @click="submit" :disabled="isSubmitting || !name" class="mt-n4">
              {{ $t("modal.timeline.duplicate.update") }}
            </v-btn>
          </v-row>
        </v-col>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
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

const timelineStore = useTimelineStore();

const dialog = ref(props.modelValue);
const isSubmitting = ref(false);
const nameProxy = ref(null);
const includeannotations = ref(true);

const name = computed({
  get() {
    const timelineName = timelineStore.timelines[props.timeline].name + " (1)";
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
